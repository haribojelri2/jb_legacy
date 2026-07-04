"""Playwright E2E tests for JB Legacy Streamlit UI."""

import re
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8502"


@pytest.fixture(autouse=True)
def goto_app(page: Page, streamlit_server):
    # streamlit_server: conftest가 서버를 확보(자동 기동)하거나 없으면 이 파일 전체를 skip
    page.goto(streamlit_server)
    page.wait_for_load_state("networkidle")


def _go_step2(page: Page):
    page.locator("button").filter(has_text=re.compile("시작하기")).click()
    page.wait_for_load_state("networkidle")


# ── Step 1 ────────────────────────────────────────────────────────────────────

def test_step1_logo_visible(page: Page):
    # .first: "JB Legacy"가 여러 요소(로고·헤더)에 나올 수 있어 strict-mode 다중매칭 방지
    expect(page.locator("text=JB Legacy").first).to_be_visible(timeout=8000)


def test_step1_persona_radio_visible(page: Page):
    expect(page.locator("text=이사장")).to_be_visible()
    expect(page.locator("text=김소장")).to_be_visible()
    expect(page.locator("text=박원장")).to_be_visible()
    expect(page.locator("text=최대표")).to_be_visible()


def test_step1_sajang_shows_form(page: Page):
    expect(page.locator("text=세부 조건 조정")).to_be_visible()
    expect(page.locator("button").filter(has_text=re.compile("분석 시작하기"))).to_be_visible()


def test_step1_to_step2_navigation(page: Page):
    _go_step2(page)
    expect(page.locator("text=대화")).to_be_visible(timeout=8000)


# ── Step 2 ────────────────────────────────────────────────────────────────────

def test_step2_chat_input_visible(page: Page):
    _go_step2(page)
    expect(page.get_by_test_id("stChatInputTextArea")).to_be_visible(timeout=8000)


def test_step2_analysis_panel_hidden_initially(page: Page):
    _go_step2(page)
    # 분석 결과 패널은 결과가 없을 때 보이지 않아야 함
    expect(page.locator("text=분석 결과")).not_to_be_visible(timeout=3000)


def test_step2_back_button(page: Page):
    _go_step2(page)
    page.locator("button").filter(has_text="처음으로").click()
    page.wait_for_load_state("networkidle")
    expect(page.locator("text=분석 시작하기").first).to_be_visible(timeout=8000)
    expect(page.locator("text=대화")).not_to_be_visible(timeout=3000)


def test_step2_child_sharing_flow(page: Page):
    _go_step2(page)
    page.locator("button").filter(has_text=re.compile("폐업할지 승계할지")).click()
    # Wait for the analysis result panel to appear (up to 120 seconds, as multi-agent LLM analysis can take ~80 seconds)
    expect(page.locator("text=세금 비교")).to_be_visible(timeout=120000)
    # Click on "가족 협상(D안)" tab
    page.locator("button").filter(has_text="가족 협상(D안)").click()
    # Click sharing button
    page.locator("button").filter(has_text="이과장에게 공유").click()
    # Click "이과장이(가) 링크 열기" button
    page.locator("button").filter(has_text="링크 열기").click()
    # Verify child dashboard elements
    expect(page.locator("text=아버지(이사장) 은퇴 플랜 리포트")).to_be_visible(timeout=10000)
    expect(page.locator("text=이과장의 협상 제안")).to_be_visible()


def test_step2_casual_message_no_analysis_panel(page: Page):
    """인사 메시지는 분석 패널을 열지 않아야 함."""
    _go_step2(page)
    chat_input = page.get_by_test_id("stChatInputTextArea")
    chat_input.fill("ㅎㅇ")
    chat_input.press("Enter")
    # LLM 응답 대기 (최대 15초)
    page.wait_for_timeout(15000)
    expect(page.locator("text=분석 결과")).not_to_be_visible(timeout=2000)
