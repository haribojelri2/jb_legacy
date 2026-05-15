"""Playwright E2E tests for JB Legacy Streamlit UI."""

import re
import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8502"


@pytest.fixture(autouse=True)
def goto_app(page: Page):
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")


def _go_step2(page: Page):
    page.locator("button").filter(has_text=re.compile("시작하기")).click()
    page.wait_for_load_state("networkidle")


# ── Step 1 ────────────────────────────────────────────────────────────────────

def test_step1_logo_visible(page: Page):
    expect(page.locator("text=JB Legacy")).to_be_visible()


def test_step1_persona_radio_visible(page: Page):
    expect(page.locator("text=이사장")).to_be_visible()
    expect(page.locator("text=이과장")).to_be_visible()


def test_step1_sajang_shows_form(page: Page):
    expect(page.locator("text=따님 승계 의향")).to_be_visible()
    expect(page.locator("button").filter(has_text=re.compile("시작하기"))).to_be_visible()


def test_step1_gwajang_shows_info(page: Page):
    page.locator("label").filter(has_text="이과장").click()
    page.wait_for_timeout(500)
    expect(page.locator("button").filter(has_text="이과장 화면 열기")).to_be_visible()
    expect(page.locator("text=따님 승계 의향")).not_to_be_visible()


def test_step1_to_step2_navigation(page: Page):
    _go_step2(page)
    expect(page.locator("text=대화")).to_be_visible(timeout=8000)


# ── Step 2 ────────────────────────────────────────────────────────────────────

def test_step2_chat_input_visible(page: Page):
    _go_step2(page)
    expect(page.get_by_test_id("stChatInputTextArea")).to_be_visible(timeout=8000)


def test_step2_analysis_panel_hidden_initially(page: Page):
    _go_step2(page)
    # 분析 결과 패널은 결과가 없을 때 보이지 않아야 함
    expect(page.locator("text=분析 결과")).not_to_be_visible(timeout=3000)


def test_step2_back_button(page: Page):
    _go_step2(page)
    page.locator("button").filter(has_text="처음으로").click()
    page.wait_for_load_state("networkidle")
    expect(page.locator("text=JB Legacy")).to_be_visible(timeout=5000)
    expect(page.locator("text=대화")).not_to_be_visible(timeout=3000)


def test_step2_casual_message_no_analysis_panel(page: Page):
    """인사 메시지는 분析 패널을 열지 않아야 함."""
    _go_step2(page)
    chat_input = page.get_by_test_id("stChatInputTextArea")
    chat_input.fill("ㅎㅇ")
    chat_input.press("Enter")
    # LLM 응답 대기 (최대 15초)
    page.wait_for_timeout(15000)
    expect(page.locator("text=분析 결과")).not_to_be_visible(timeout=2000)
