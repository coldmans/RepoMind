# 사용할 파이썬 공식 이미지를 기반으로 시작합니다.
FROM python:3.10-slim-bookworm

# apt-get을 업데이트하고 필요한 패키지 (예: git)를 설치합니다.
# 디스코드 봇 자체는 git이 필요 없을 수 있지만, 혹시 모를 경우를 대비합니다.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 컨테이너 내부의 작업 디렉토리를 설정합니다.
WORKDIR /app

# requirements.txt 파일을 복사하고 의존성을 설치합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 봇 코드 파일을 컨테이너로 복사합니다.
COPY . .

# 봇 실행 명령을 정의합니다. (예: bot.py가 메인 파일일 경우)
CMD ["python", "bot.py"]