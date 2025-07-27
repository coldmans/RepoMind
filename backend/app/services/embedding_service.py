# backend/app/services/embedding_service.py

import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

# OpenAI 클라이언트 초기화
# 환경 변수 OPENAI_API_KEY가 설정되어 있어야 합니다.
client = OpenAI()

# 사용할 임베딩 모델 이름 (OpenAI 기준)
EMBEDDING_MODEL = "text-embedding-3-small" # 또는 "text-embedding-3-large" (더 정확하지만 비용 높음)

async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    주어진 텍스트 리스트에 대한 임베딩 벡터를 생성합니다.
    """
    if not texts:
        return []

    try:
        # OpenAI 임베딩 API 호출
        response = client.embeddings.create(
            input=texts,
            model=EMBEDDING_MODEL
        )
        # 응답에서 임베딩 벡터만 추출하여 반환
        embeddings = [data.embedding for data in response.data]
        logger.info(f"성공적으로 {len(texts)}개 텍스트에 대한 임베딩 생성 완료.")
        return embeddings

    except Exception as e:
        logger.error(f"임베딩 생성 중 오류 발생: {e}")
        raise # 오류를 다시 발생시켜 상위 호출자에게 알립니다.