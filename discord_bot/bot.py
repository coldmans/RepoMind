# discord_bot/bot.py

import os
import json
import httpx # 백엔드 API 호출용
import discord
from discord.ext import commands
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env 파일에서 환경 변수 로드 (Docker Compose가 자동으로 해줌)
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://backend:8000") # Docker Compose 내부 통신 URL

# 디스코드 봇의 인텐트(Intent) 설정
# 봇이 어떤 이벤트를 수신할지 정의합니다.
# 메시지 내용, 길드 멤버 정보 등을 읽으려면 해당 인텐트가 필요합니다.
intents = discord.Intents.default()
intents.message_content = True # 메시지 내용 읽기 권한
intents.members = True # 길드 멤버 정보 (선택 사항, 필요 시)

# 봇 클라이언트 초기화
# command_prefix는 봇 명령의 시작 문자입니다 (예: !ask)
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """봇이 Discord에 성공적으로 연결되었을 때 실행됩니다."""
    logger.info(f"봇 로그인 완료: {bot.user.name} (ID: {bot.user.id})")
    print(f"봇 로그인 완료: {bot.user.name} (ID: {bot.user.id})")
    print("--------------------------------------------------")

@bot.event
async def on_command_error(ctx, error):
    """명령어 실행 중 오류 발생 시 처리합니다."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("알 수 없는 명령어입니다. `!도움말`을 입력해보세요.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("명령어에 필요한 인수가 부족합니다. `!도움말`을 참조하세요.")
    else:
        logger.error(f"명령어 실행 중 오류 발생: {error}")
        await ctx.send(f"오류가 발생했습니다: {error}")

@bot.command(name="안녕", help="봇이 인사를 합니다.")
async def hello(ctx):
    """봇이 인사를 합니다."""
    await ctx.send(f"안녕하세요, {ctx.author.display_name}님!")

@bot.command(name="레포추가", help="GitHub 레포지토리를 추가합니다. 사용법: !레포추가 [레포URL] [레포이름] [브랜치(선택)]")
async def add_repo(ctx, repo_url: str, repo_name: str, branch: str = "main"):
    """
    GitHub 레포지토리를 클론하고 벡터 DB에 저장합니다.
    """
    await ctx.send(f"'{repo_name}' 레포지토리({repo_url})를 처리 중입니다. 시간이 다소 걸릴 수 있습니다...")

    try:
        # 백엔드 API 호출
        async with httpx.AsyncClient() as client_http:
            response = await client_http.post(
                f"{BACKEND_API_URL}/repo/process",
                params={
                    "repo_url": repo_url,
                    "repo_name": repo_name,
                    "branch": branch
                },
                timeout=600.0  # 레포지토리 처리는 시간이 오래 걸릴 수 있음
            )
            response.raise_for_status()

            result = response.json()
            total_chunks = result.get("total_chunks_processed", 0)
            
            await ctx.send(f"✅ '{repo_name}' 레포지토리가 성공적으로 추가되었습니다!\n총 {total_chunks}개의 코드 청크가 처리되었습니다.")

    except httpx.HTTPStatusError as e:
        logger.error(f"백엔드 API HTTP 오류: {e.response.status_code} - {e.response.text}")
        error_detail = "알 수 없는 오류"
        try:
            error_json = e.response.json()
            error_detail = error_json.get('detail', '알 수 없는 오류')
        except:
            error_detail = e.response.text
        await ctx.send(f"❌ 레포지토리 추가 중 오류가 발생했습니다 (HTTP {e.response.status_code}): {error_detail}")
    except httpx.RequestError as e:
        logger.error(f"백엔드 API 요청 오류: {e}")
        await ctx.send(f"❌ 백엔드 서버와 통신할 수 없습니다: {BACKEND_API_URL}")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        await ctx.send(f"❌ 레포지토리 추가 중 예상치 못한 오류가 발생했습니다: {e}")

@bot.command(name="레포분석", help="GitHub 레포지토리를 분석하고 질문에 답변합니다. 사용법: !레포분석 [레포이름] [질문]")
async def analyze_repo(ctx, repo_name: str, *, query: str):
    """
    GitHub 레포지토리의 정보를 분석하고 질문에 답변합니다.
    """
    await ctx.send(f"'{repo_name}' 레포지토리에 대해 '{query}' 질문을 처리 중입니다. 잠시만 기다려 주세요...")

    try:
        # 백엔드 API 호출
        async with httpx.AsyncClient() as client_http:
            response = await client_http.post(
                f"{BACKEND_API_URL}/repo/query",
                params={
                    "query_text": query,
                    "repo_name": repo_name,
                    "n_results": 5 # 가져올 청크 수
                },
                timeout=300.0 # 응답이 길어질 수 있으므로 타임아웃을 넉넉하게 설정
            )
            response.raise_for_status() # HTTP 오류 발생 시 예외 처리

            result = response.json()
            ai_response = result.get("ai_response", "답변을 생성할 수 없습니다.")

            # 디스코드 메시지 길이 제한 (2000자)을 고려하여 분할 전송
            if len(ai_response) > 2000:
                await ctx.send("답변이 너무 길어 요약하여 전달합니다:")
                # 긴 답변을 여러 메시지로 분할하여 보내는 로직 (간단화)
                for i in range(0, len(ai_response), 1900):
                    await ctx.send(ai_response[i:i+1900])
            else:
                await ctx.send(ai_response)

            # AI가 참조한 소스 청크도 함께 보여줄 수 있습니다.
            # source_chunks = result.get("source_chunks", [])
            # if source_chunks:
            #     source_info = "\n\n**참조된 코드/문서:**\n"
            #     for chunk in source_chunks:
            #         meta = chunk.get("metadata", {})
            #         source_info += f"- `{meta.get('file_path', '알 수 없는 파일')}` (언어: {meta.get('language', '알 수 없음')})\n"
            #     await ctx.send(source_info)

    except httpx.HTTPStatusError as e:
        logger.error(f"백엔드 API HTTP 오류: {e.response.status_code} - {e.response.text}")
        await ctx.send(f"백엔드에서 오류가 발생했습니다 (HTTP {e.response.status_code}): {e.response.json().get('detail', '알 수 없는 오류')}")
    except httpx.RequestError as e:
        logger.error(f"백엔드 API 요청 오류: {e}")
        await ctx.send(f"백엔드 서버와 통신할 수 없습니다. 서버가 실행 중인지 확인해주세요: {BACKEND_API_URL}")
    except json.JSONDecodeError:
        logger.error(f"백엔드 API 응답 JSON 파싱 오류: {response.text}")
        await ctx.send("백엔드에서 유효하지 않은 응답을 받았습니다.")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        await ctx.send(f"명령어 처리 중 예상치 못한 오류가 발생했습니다: {e}")

# 봇 실행
if __name__ == "__main__":
    if not DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN 환경변수가 설정되지 않았습니다.")
        exit(1)
    
    logger.info("Discord 봇을 시작합니다...")
    bot.run(DISCORD_BOT_TOKEN)