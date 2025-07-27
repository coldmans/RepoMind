# backend/app/services/vector_db_service.py

import logging
from typing import List, Dict, Any
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# ChromaDB 클라이언트 초기화
# 이 예시에서는 로컬 파일 시스템에 데이터를 저장합니다.
# docker-compose.yml의 volumes 설정과 일치해야 합니다.
CHROMA_DB_PATH = "./chroma_db"
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# 기본 임베딩 함수 설정 (ChromaDB가 자체적으로 임베딩을 생성할 때 사용)
# 우리는 외부 서비스(OpenAI/Anthropic)에서 임베딩을 가져올 것이므로 이 함수는 사용하지 않습니다.
# 하지만 클라이언트를 초기화하기 위해 필요할 수 있습니다.
# ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")


async def get_or_create_collection(collection_name: str):
    """
    주어진 이름의 ChromaDB 컬렉션을 가져오거나 새로 생성합니다.
    """
    try:
        # 컬렉션이 없으면 새로 생성 (create_if_not_exists=True)
        collection = client.get_or_create_collection(name=collection_name)
        logger.info(f"ChromaDB 컬렉션 '{collection_name}' 가져오기/생성 완료.")
        return collection
    except Exception as e:
        logger.error(f"ChromaDB 컬렉션 생성/가져오기 중 오류 발생: {e}")
        raise

async def add_documents_to_collection(
    collection_name: str,
    documents: List[str], # 청크 텍스트 리스트
    metadatas: List[Dict[str, Any]], # 청크 메타데이터 리스트
    embeddings: List[List[float]], # 생성된 임베딩 벡터 리스트
    ids: List[str] # 각 문서의 고유 ID 리스트
):
    """
    ChromaDB 컬렉션에 문서, 메타데이터, 임베딩을 추가합니다.
    """
    try:
        collection = await get_or_create_collection(collection_name)
        # add 메서드는 list 형태로 받습니다.
        collection.add(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )
        logger.info(f"컬렉션 '{collection_name}'에 {len(documents)}개 문서 추가 완료.")
    except Exception as e:
        logger.error(f"ChromaDB에 문서 추가 중 오류 발생: {e}")
        raise

async def query_collection(
    collection_name: str,
    query_texts: List[str] = None, # 쿼리할 텍스트 (직접 임베딩 생성)
    query_embeddings: List[List[float]] = None, # 쿼리 임베딩 (미리 생성된 경우)
    n_results: int = 5,
    where: Dict[str, Any] = None, # 메타데이터 필터링 조건
    where_document: Dict[str, Any] = None # 문서 내용 필터링 조건
) -> List[Dict[str, Any]]:
    """
    ChromaDB 컬렉션에서 쿼리를 실행하고 결과를 반환합니다.
    """
    try:
        collection = await get_or_create_collection(collection_name)
        results = collection.query(
            query_texts=query_texts,
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
            where_document=where_document
            # include=['documents', 'metadatas', 'distances'] # 어떤 정보를 반환할지
        )
        logger.info(f"컬렉션 '{collection_name}'에서 쿼리 실행 완료. {len(results['documents'][0]) if results['documents'] else 0}개 결과.")
        # ChromaDB 결과 형식을 필요한 부분만 추출하여 반환
        processed_results = []
        if results['documents']:
            for i in range(len(results['documents'][0])):
                processed_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i]
                })
        return processed_results
    except Exception as e:
        logger.error(f"ChromaDB 쿼리 중 오류 발생: {e}")
        raise