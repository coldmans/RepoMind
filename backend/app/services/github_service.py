import os
import shutil
from git import Repo, GitCommandError
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def clone_repository(repo_url: str, local_path: Path, branch: str = "main", github_pat: str = None) -> bool:
    """
    GitHub 레포지토리를 지정된 로컬 경로로 클론합니다.
    이미 존재하면 pull하여 최신 상태로 업데이트합니다.
    """
    if local_path.exists() and local_path.is_dir():
        logger.info(f"레포지토리 {repo_url}가 이미 {local_path}에 존재합니다. 최신 상태로 업데이트합니다.")
        try:
            repo = Repo(local_path)
            #원격 오리진을 fetch하고 현재 브랜치를 pull함
            #GitPython은 PAT를 URL에 직접 포함하여 인증함
            if github_pat:
                #PAT를 사용하여 인증된 URL 생성 (HTTPS 방식)
                repo_url_with_pat = repo_url.replace("https://github.com/", f"https://oauth2:{github_pat}@github.com/")
                repo.remotes.origin.set_url(repo_url_with_pat) #PAT가 변경될 경우 URL 업데이트
            repo.git.checkout(branch)
            repo.remotes.origin.pull(branch)
            logger.info(f"레포지토리 {repo_url}가 성공적으로 업데이트되었습니다.")
            return True
        except GitCommandError as e:
            logger.error(f"레포지토리 업데이트 중 Git 오류 발생: {e}")
            return False
        except Exception as e:
            logger.error(f"레포지토리 업데이트 중 오류 발생: {e}")
            return False
    else:
        logger.info(f"레포지토리 {repo_url}를 {local_path}에 클론합니다.")
        try:
            #PAT를 사용하여 인증된 URL 생성 (HTTPS 방식)
            if github_pat:
                repo_url = repo_url.replace("https://github.com/", f"https://oauth2:{github_pat}@github.com/")
            Repo.clone_from(repo_url, local_path, branch=branch)
            logger.info(f"레포지토리 {repo_url} 클론 완료. ")
            return True
        except GitCommandError as e:
            logger.error(f"레포지토리 클론 중 Git 오류 발생 : {e}")
            if local_path.exists() and local_path.is_dir():
                shutil.rmtree(local_path)
            return False
        except Exception as e:
            logger.error(f"레포지토리 클론 중 예상치 못한 오류 발생: {e}")
            return False

def get_repo_files(repo_path: Path, ignore_patterns : list = None) -> list[Path]:
    """
    레포지토리 경로에서 모든 파일 목록을 가져옵니다
    .gitignore 패턴을 기반으로 파일을 제외할 수 있습니다.
    """
    if not repo_path.is_dir():
        logger.error(f"레포지토리 경로가 유효하지 않습니다: {repo_path}")
        return []
    
    file_paths = []
    #.gitignore 파일을 처리하기 위한 로직 (나중에 pathspec 라이브러리 활용하면 더 좋음)
    #일단은 간단한 예시로 특정 패턴만 무시
    default_ignore_patterns = ['.git/', '__pycache__/', '.env', '.DS_Store', 'node_modules/', 'venv/']
    if ignore_patterns:
        default_ignore_patterns.extend(ignore_patterns)
    
    for root, dirs, files in os.walk(repo_path):
        # 무시할 디렉토리 처리 (os.walk 최적화)
        # '.'으로 시작하는 디렉토리와 ignore_patterns에 있는 디렉토리는 건너뜀
        dirs[:] = [d for d in dirs if not d.startswith('.') and f"{d}/" not in default_ignore_patterns]

        for file in files:
            file_path = Path(root) / file
            relative_path = file_path.relative_to(repo_path)

            # 무시할 파일 패턴 확인
            should_ignore = False
            for pattern in default_ignore_patterns:
                if pattern.endswith('/') and str(relative_path).startswith(pattern.rstrip('/')):
                    should_ignore = True
                    break
                elif str(relative_path) == pattern: # 정확히 일치하는 파일 이름
                    should_ignore = True
                    break
                elif pattern.startswith('.') and str(file_path.name).startswith(pattern): # 예: .DS_Store, .env
                    should_ignore = True
                    break
                elif '*' in pattern and Path(str(relative_path)).match(pattern): # 와일드카드 패턴 지원 (간단한 형태)
                    should_ignore = True
                    break

            if not should_ignore:
                file_paths.append(file_path)

    return file_paths

def read_file_content(file_path: Path) -> str | None:
    """
    파일 내용을 읽어서 문자열로 반환합니다.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        logger.warning(f"파일 {file_path}를 UTF-8로 디코딩할 수 없습니다. 다른 인코딩 시도 또는 스킵.")
        # 다른 인코딩 시도 또는 바이너리 파일 스킵 로직 추가 가능
        try:
            with open(file_path, 'r', encoding='latin-1') as f: # 주로 서유럽 언어 인코딩
                return f.read()
        except Exception as e:
            logger.error(f"파일 {file_path} 읽기 오류: {e}")
            return None
    except Exception as e:
        logger.error(f"파일 {file_path} 읽기 오류: {e}")
        return None