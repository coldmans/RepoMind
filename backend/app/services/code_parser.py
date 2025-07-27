import logging
from pathlib import Path

logger = logging.getLogger(__name__)

#청크가 포함할 최대 글자 수~
CHUNK_SIZE = 1000
#청크 간의 겹치는 부분이요~
CHUNK_OVERLAP = 200

def get_file_language(file_path: Path) -> str:
    """파일 확장자를 기반으로 언어를 추정합니다."""
    ext = file_path.suffix.lower()
    if ext == '.py':
        return 'python'
    elif ext == '.java':
        return 'java'
    elif ext == '.js' or ext == '.ts':
        return 'javascript/typescript'
    elif ext == '.md' or ext == '.markdown':
        return 'markdown'
    elif ext == '.c' or ext == '.cpp':
        return 'c/cpp'
    elif ext == '.go':
        return 'go'
    elif ext == '.rs':
        return 'rust'
    elif ext == '.json':
        return 'json'
    elif ext == '.xml':
        return 'xml'
    else:
        return 'unknown' # 또는 'text'

def chunk_text(text: str, file_path: Path, repo_name: str) -> list[dict]:
    """
    주어진 텍스트를 청크로 분할하고 메타데이터를 추가합니다.
    (간단한 글자 수 기반 청크 분할)
    """
    chunks = []
    text_len = len(text)
    start_idx = 0
    chunk_num = 0

    language = get_file_language(file_path)

    while start_idx < text_len:
        end_idx = min(start_idx + CHUNK_SIZE, text_len)
        chunk_content = text[start_idx:end_idx]

        # 줄 번호 정보는 정확히 계산하기 어려우므로, 간단히 0으로 표기하거나 생략
        # AST 파싱을 통해 정확한 줄 번호를 얻을 수 있지만, 여기서는 간단히 처리
        start_line = 0 # Placeholder for now
        end_line = 0   # Placeholder for now

        metadata = {
            "file_path": str(file_path.relative_to(file_path.parts[0])), # 레포 루트 기준 상대 경로
            "repo_name": repo_name,
            "language": language,
            "chunk_index": chunk_num,
            "start_char": start_idx,
            "end_char": end_idx,
            "start_line": start_line, # 추후 개선 필요
            "end_line": end_line,     # 추후 개선 필요
            # "git_commit_info": "..." # Git 정보도 추가 가능
        }
        
        chunks.append({
            "content": chunk_content,
            "metadata": metadata
        })

        # 다음 청크 시작 위치 계산 (오버랩 적용)
        start_idx += CHUNK_SIZE - CHUNK_OVERLAP
        chunk_num += 1

    return chunks

