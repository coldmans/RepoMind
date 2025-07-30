# backend/app/main.py (기존 내용에 추가/수정)

from fastapi import FastAPI, HTTPException
import os
from pathlib import Path
import logging
import uuid # 청크 ID 생성을 위해 추가

# services 모듈 임포트
from app.services.github_service import clone_repository, get_repo_files, read_file_content
from app.services.code_parser import chunk_text # AST 파싱은 일단 제외하고 단순 청크 사용
from app.services.embedding_service import get_embeddings # 새로 추가
from app.services.vector_db_service import add_documents_to_collection, query_collection # 새로 추가
from app.services.llm_service import generate_response_from_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

GITHUB_PAT = os.getenv("GITHUB_PAT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # OpenAI API 키도 확인
REPOS_DIR = Path("./data/repos")

# ChromaDB 컬렉션 이름 (레포지토리별로 다르게 관리하는 것도 좋음)
# 여기서는 예시를 위해 고정된 이름 사용
CHROMA_COLLECTION_NAME = "repo_code_chunks" 


@app.get("/")
async def read_root():
    return {"message": "Hello, RepoMind Backend!"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/repo/process")
async def process_repo(
    repo_url: str,
    repo_name: str,
    branch: str = "main"
):
    """
    지정된 GitHub 레포지토리를 클론하고, 파일을 읽어 청크로 분할하고,
    임베딩을 생성하여 벡터 DB에 저장합니다.
    """
    if not GITHUB_PAT:
        raise HTTPException(status_code=400, detail="GITHUB_PAT 환경 변수가 설정되지 않았습니다. 개인 액세스 토큰을 .env 파일에 추가해주세요.")
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

    local_repo_path = REPOS_DIR / repo_name

    REPOS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"레포지토리 {repo_url} 클론 또는 업데이트 시작.")
    success = clone_repository(repo_url, local_repo_path, branch, GITHUB_PAT)

    if not success:
        raise HTTPException(status_code=500, detail=f"레포지토리 클론 또는 업데이트 실패: {repo_url}")

    logger.info(f"레포지토리 {repo_name} 파일 스캔 및 청크 생성 시작.")
    file_paths = get_repo_files(local_repo_path)

    all_chunk_contents = []
    all_chunk_metadatas = []
    all_chunk_ids = []

    for path in file_paths:
        content = read_file_content(path)
        if content and content.strip(): # 내용이 비어있지 않은 파일만 처리
            chunks_from_file = chunk_text(content, path, repo_name)
            for chunk in chunks_from_file:
                all_chunk_contents.append(chunk["content"])
                all_chunk_metadatas.append(chunk["metadata"])
                all_chunk_ids.append(str(uuid.uuid4())) # 각 청크에 고유 ID 부여
        else:
            logger.warning(f"파일 내용이 비어있거나 읽기 실패: {path}")

    if not all_chunk_contents:
        return {
            "message": f"레포지토리 {repo_name}에서 처리할 유효한 청크가 없습니다.",
            "repo_path": str(local_repo_path),
            "total_files": len(file_paths),
            "total_chunks": 0
        }

    logger.info(f"총 {len(file_paths)}개 파일에서 {len(all_chunk_contents)}개 청크 생성 완료. 임베딩 시작.")

    # 임베딩 생성 (비동기 함수이므로 await 사용)
    try:
        embeddings = await get_embeddings(all_chunk_contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"임베딩 생성 중 오류 발생: {e}")

    logger.info(f"총 {len(embeddings)}개 임베딩 생성 완료. 벡터 DB 저장 시작.")

    # 벡터 DB에 저장 (비동기 함수이므로 await 사용)
    try:
        await add_documents_to_collection(
            CHROMA_COLLECTION_NAME,
            all_chunk_contents,
            all_chunk_metadatas,
            embeddings,
            all_chunk_ids
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"벡터 DB 저장 중 오류 발생: {e}")


    return {
        "message": f"레포지토리 {repo_name} 처리, 청크 생성, 임베딩 및 벡터 DB 저장 완료",
        "repo_path": str(local_repo_path),
        "total_files": len(file_paths),
        "total_chunks_processed": len(all_chunk_contents)
        # "sample_chunks": all_chunks[:5] # 이제 샘플 청크는 응답으로 직접 보내지 않고, 벡터 DB에 저장
    }

# --- (추가 API: 벡터 DB에서 쿼리하는 엔드포인트) ---
@app.post("/repo/query")
async def query_repo(query_text: str, repo_name: str = None, n_results: int = 5):
    """
    벡터 DB에 저장된 레포지토리 정보에 대해 질의하고 AI 답변을 반환합니다.
    """
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

    logger.info(f"쿼리 '{query_text}'에 대한 임베딩 생성 시작.")
    try:
        query_embedding = await get_embeddings([query_text])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"쿼리 임베딩 생성 중 오류 발생: {e}")

    logger.info(f"벡터 DB에서 관련 컨텍스트 검색 시작 (쿼리: '{query_text}').")
    where_clause = {}
    if repo_name:
        where_clause["repo_name"] = repo_name

    try:
        context_results = await query_collection(
            CHROMA_COLLECTION_NAME,
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where_clause if where_clause else None
        )
        logger.info(f"벡터 DB에서 {len(context_results)}개 컨텍스트 청크 검색 완료.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"벡터 DB 쿼리 중 오류 발생: {e}")

    logger.info(f"AI 모델을 사용하여 답변 생성 시작 (쿼리: '{query_text}').")
    try:
        ai_response = await generate_response_from_context(query_text, context_results)
        logger.info("AI 답변 생성 완료.")
        return {
            "message": "AI 답변",
            "query": query_text,
            "ai_response": ai_response,
            "source_chunks_count": len(context_results),
            "source_chunks": context_results
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"AI 답변 생성 중 예상치 못한 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"AI 답변 생성 중 오류 발생: {e}")