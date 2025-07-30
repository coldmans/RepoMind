#backend/app/services/llm_service.py

import os
import logging
from openai import OpenAI, APIStatusError
from typing import List, Dict, Any
from fastapi import HTTPException 

logger = logging.getLogger(__name__)
client = OpenAI()

LLM_MODEL = 'gpt-4o-mini'

async def generate_response_from_context(
        query : str,
        context_chunks : List[Dict[str, Any]],
        model : str = LLM_MODEL
) -> str:
    """
    주어진 질문과 컨텍스트 청크를 바탕으로 AI 모델에게 답변을 생성하도록 요청
    """
    if not context_chunks:
        logger.warning("컨텍스트 청크가 없어 AI 답변 생성에 제약이 있을 수 있습니다.")
        system_message_content = (
            "너는 개발자를 돕는 레포지토리 분석 AI 에이전트다"
            "주어진 컨텍스트가 없는 경우에도 질문에 최선을 다해 답변 해"
            "컨텍스트가 부족하면 부족하다고 말해"
        )
        context_text = "제공된 코드/문서가 없어요."
    else:
        context_parts = []
        for i, chunk in enumerate(context_chunks):
            metadata = chunk.get("metadata", {})
            content = chunk.get("content", "내용 없음")
            file_path = metadata.get("file_path", "경로 알 수 없음")
            language = metadata.get("language", "알 수 없음")
            
            context_parts.append(f"--- 파일: {file_path} (언어: {language}, 청크 {i+1}) ---\n{content}\n---")
        
        context_text = "\n\n".join(context_parts)
        
        system_message_content = (
            "당신은 개발자를 돕는 레포지토리 분석 AI 에이전트입니다. "
            "사용자의 질문에 대해 아래 제공된 코드/문서 컨텍스트를 기반으로 정확하고 상세하게 답변해 주세요. "
            "컨텍스트에 없는 내용은 추측하지 마세요. "
            "코드를 인용할 때는 실제 코드 스니펫을 사용하여 설명하세요. "
            "답변은 한국어로 해주세요."
        )
    
    messages = [
        {"role": "system", "content": system_message_content},
        {"role": "user", "content": f"다음 컨텍스트를 사용하여 내 질문에 답변해 주세요:\n\n컨텍스트:\n{context_text}\n\n질문: {query}"}
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7, # 창의성 조절 (0.0은 가장 보수적, 1.0은 가장 창의적)
            max_tokens=1000 # AI 답변의 최대 길이
        )
        ai_response_content = response.choices[0].message.content
        logger.info(f"AI 모델({model})로부터 답변 생성 완료. 사용 토큰: {response.usage.total_tokens}")
        return ai_response_content

    except APIStatusError as e:
        logger.error(f"AI 모델 API 호출 중 오류 발생 (상태 코드: {e.status_code}): {e.response.json()}")
        if e.status_code == 429:
            raise HTTPException(status_code=500, detail=f"AI 모델 할당량/Rate Limit 오류: {e.response.json().get('error', {}).get('message', '알 수 없는 오류')}")
        raise HTTPException(status_code=500, detail=f"AI 모델 API 오류: {e.response.json().get('error', {}).get('message', '알 수 없는 오류')}")
    except Exception as e:
        logger.error(f"AI 모델 답변 생성 중 예상치 못한 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"AI 모델 답변 생성 오류: {e}")