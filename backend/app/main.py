# backend/app/main.py (기존 내용에 추가)

from fastapi import FastAPI, HTTPException
import os
from pathlib import Path
import logging

# services 모듈 임포트
from app.services.github_service import clone_repository, get_repo_files, read_file_content

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

@app.post("/repo/clone")
async def clone_and_list_repo(
    repo_url: str,
    repo_name: str, # 클론될 로컬 폴더 이름으로 사용
    branch: str = "main"
):
    """
    지정된 GitHub 레포지토리를 클론하고, 클론된 레포지토리의 파일 목록을 반환합니다.
    """
    if not GITHUB_PAT:
        raise HTTPException(status_code=400, detail="GITHUB_PAT 환경 변수가 설정되지 않았습니다. 개인 액세스 토큰을 .env 파일에 추가해주세요.")

    local_repo_path = REPOS_DIR / repo_name

    # 레포지토리 저장 디렉토리가 없으면 생성
    REPOS_DIR.mkdir(parents=True, exist_ok=True)

    success = clone_repository(repo_url, local_repo_path, branch, GITHUB_PAT)

    if not success:
        raise HTTPException(status_code=500, detail=f"레포지토리 클론 또는 업데이트 실패: {repo_url}")

    file_paths = get_repo_files(local_repo_path)

    # 파일 내용까지 읽는 예시 (실제 사용 시에는 청크 분할 로직에서 처리)
    file_contents = []
    for path in file_paths:
        content = read_file_content(path)
        if content:
            # 너무 긴 내용은 잘라내서 예시로 보여줌
            file_contents.append({
                "path": str(path.relative_to(local_repo_path)),
                "size": len(content),
                "content_preview": content[:200] + "..." if len(content) > 200 else content
            })

    return {
        "message": f"레포지토리 {repo_name} 클론 및 파일 목록 가져오기 성공",
        "repo_path": str(local_repo_path),
        "total_files": len(file_paths),
        "files": file_contents
    }