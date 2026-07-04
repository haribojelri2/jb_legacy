import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

# 프로젝트 루트를 import 경로에 추가 (tools/, agents/ 임포트용)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

_UI_PORT = 8502
_UI_URL = f"http://localhost:{_UI_PORT}"


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("localhost", port)) == 0


def _http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def streamlit_server():
    """UI E2E용 Streamlit 서버 확보 — 이미 떠 있으면 재사용, 없으면 자동 기동.

    - 서버가 이미 8502에 있으면 그대로 사용(수동 기동 호환).
    - 없고 API 키가 있으면 자동 기동 후 헬스체크 폴링, 세션 종료 시 정리.
    - 자동 기동이 불가(키 없음·기동 실패)하면 UI 테스트를 skip해 pytest가 깨지지 않게 함.
    """
    if _port_open(_UI_PORT) and _http_ok(_UI_URL):
        yield _UI_URL
        return

    # app.py 시작 가드가 요구하는 키(OpenAI + 기본 Claude)가 없으면 자동 기동 불가
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_ROOT, ".env"))
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("Streamlit 서버 미기동 · OPENAI_API_KEY 없음 — UI E2E 건너뜀")

    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "ui/app.py",
         "--server.port", str(_UI_PORT), "--server.headless", "true"],
        cwd=_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(40):  # 최대 ~40초 대기
            if _http_ok(_UI_URL):
                break
            time.sleep(1)
        else:
            proc.terminate()
            pytest.skip("Streamlit 서버 자동 기동 실패 — UI E2E 건너뜀")
        yield _UI_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
