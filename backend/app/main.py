# backend/app/main.py (기존 내용에 추가/수정)

from fastapi import FastAPI, HTTPException
import os
from pathlib import Path
import logging

# services 모듈 임포트
from app.services.github_service import clone_repository, get_repo_files, read_file_content
from app.services.code_parser import chunk_text, get_file_language # 새로 추가/수정

# 로그 설정 (개발용)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# .env 파일에서 환경 변수 로드 (Docker Compose가 자동으로 해줌)
GITHUB_PAT = os.getenv("GITHUB_PAT")
# 레포지토리가 저장될 경로
REPOS_DIR = Path("./data/repos") # Docker Compose의 volumes 설정과 일치하도록 경로 설정


@app.get("/")
async def read_root():
    return {"message": "Hello, RepoMind Backend!"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/repo/process") # 엔드포인트 이름을 clone에서 process로 변경하는 것도 고려
async def process_repo(
    repo_url: str,
    repo_name: str, # 클론될 로컬 폴더 이름으로 사용
    branch: str = "main"
):
    """
    지정된 GitHub 레포지토리를 클론하고, 파일을 읽어 청크로 분할하여 반환합니다.
    """
    if not GITHUB_PAT:
        raise HTTPException(status_code=400, detail="GITHUB_PAT 환경 변수가 설정되지 않았습니다. 개인 액세스 토큰을 .env 파일에 추가해주세요.")

    local_repo_path = REPOS_DIR / repo_name

    # 레포지토리 저장 디렉토리가 없으면 생성
    REPOS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(f"레포지토리 {repo_url} 클론 또는 업데이트 시작.")
    success = clone_repository(repo_url, local_repo_path, branch, GITHUB_PAT)

    if not success:
        raise HTTPException(status_code=500, detail=f"레포지토리 클론 또는 업데이트 실패: {repo_url}")

    logger.info(f"레포지토리 {repo_name} 파일 스캔 시작.")
    file_paths = get_repo_files(local_repo_path)

    all_chunks = []
    for path in file_paths:
        content = read_file_content(path)
        if content:
            # 파일 내용을 청크로 분할
            chunks_from_file = chunk_text(content, path, repo_name)
            all_chunks.extend(chunks_from_file)
        else:
            logger.warning(f"파일 내용 읽기 실패 또는 비어있음: {path}")

    logger.info(f"총 {len(file_paths)}개 파일에서 {len(all_chunks)}개 청크 생성 완료.")

    # 너무 많은 청크를 응답으로 보내면 API 응답이 너무 커질 수 있으니,
    # 실제 구현에서는 이 결과를 바로 벡터 DB에 저장하는 방식으로 넘어갈 겁니다.
    # 여기서는 테스트를 위해 일부만 보여줍니다.
    return {
        "message": f"레포지토리 {repo_name} 처리 및 청크 생성 완료",
        "repo_path": str(local_repo_path),
        "total_files": len(file_paths),
        "total_chunks": len(all_chunks),
        "sample_chunks": all_chunks[:5] # 처음 5개 청크만 미리보기
    }