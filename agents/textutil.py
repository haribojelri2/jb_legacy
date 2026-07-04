"""LLM 출력 텍스트 정리 유틸 — 모델 교체와 무관하게 출력 형식을 코드로 보장."""

import re


def strip_markdown(text: str) -> str:
    """마크다운 기호 제거 — 출력 규칙(번호 목록·일반 줄바꿈만 허용) 강제.

    프롬프트의 '마크다운 금지' 지시는 모델에 따라 무시될 수 있으므로
    최종 방어선으로 코드에서 제거한다. 문장 중간의 하이픈(3-5년 등)과
    ★ 강조(시니어 모드)는 보존한다.
    """
    if not text:
        return text
    lines = []
    for line in text.splitlines():
        # 수평선 라인(---, ***, ___)은 통째로 제거
        if re.fullmatch(r"\s*([-*_])\s*(?:\1\s*){2,}", line):
            continue
        # 헤더 기호 제거: "## 제목" → "제목"
        line = re.sub(r"^(\s*)#{1,6}\s+", r"\1", line)
        # 불릿 기호 제거: "- 항목" / "* 항목" / "• 항목" → "항목"
        line = re.sub(r"^(\s*)[-*•]\s+", r"\1", line)
        lines.append(line)
    out = "\n".join(lines)
    # 강조·코드 기호 제거 (**굵게**, *기울임*, `코드`)
    out = out.replace("**", "").replace("`", "").replace("*", "")
    return out
