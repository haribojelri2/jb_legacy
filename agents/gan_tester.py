"""GAN 스타일 품질 테스트 팀 — Critic(공격자) · Defender(방어자) · Judge(심판)."""

import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


# ── Pydantic 출력 모델 ────────────────────────────────────────────────────────

class CritiquePoint(BaseModel):
    category: str = Field(description="비판 카테고리: 금융정확성·규정준수·논리일관성·수치근거·편향성 중 하나")
    severity: str = Field(description="심각도: 심각·보통·경미 중 하나")
    issue: str = Field(description="구체적 문제점 1~2줄")
    suggestion: str = Field(description="개선 방향 1줄")


class CritiqueResult(BaseModel):
    points: list[CritiquePoint] = Field(description="비판 포인트 3~6개")
    overall_weakness: str = Field(description="전체 약점 요약 2~3줄")


class DefensePoint(BaseModel):
    category: str = Field(description="반박 대상 카테고리 — CritiquePoint.category와 동일")
    rebuttal: str = Field(description="반박 내용 1~2줄")
    concession: str = Field(description="인정하는 부분. 없으면 '없음'")


class DefenseResult(BaseModel):
    rebuttals: list[DefensePoint] = Field(description="카테고리별 반박")
    overall_justification: str = Field(description="전체 정당화 요약 2~3줄")


class ScoreDetail(BaseModel):
    category: str
    score: int = Field(description="0~100점")
    reason: str = Field(description="점수 근거 1줄")


class JudgeResult(BaseModel):
    scores: list[ScoreDetail]
    total_score: int = Field(description="0~100 전체 점수 (카테고리 평균)")
    verdict: str = Field(description="통과·조건부통과·재생성필요 중 하나")
    key_improvements: list[str] = Field(description="핵심 개선 사항 최대 4개")
    summary: str = Field(description="최종 판정 요약 3~4줄")


class DebateRound(BaseModel):
    round_num: int
    critique: CritiqueResult
    defense: DefenseResult


class TestReport(BaseModel):
    query: str
    rounds: list[DebateRound]
    final_score: JudgeResult


# ── 시스템 프롬프트 ───────────────────────────────────────────────────────────

_CRITIC_SYSTEM = """\
당신은 JB Legacy AI 금융 응답의 결함을 찾아내는 적대적 비평가입니다.
목표: 실제로 존재하는 문제를 최대한 구체적으로 지적해 응답 품질을 높입니다.

평가 기준:
- 금융정확성: 수치 계산 오류, 비현실적 수익률, 잘못된 세금 계산
- 규정준수: 금소법 면책고지 누락, 투자위험 미고지, 세무사 상담 권고 누락
- 논리일관성: 시나리오 간 수치 충돌, 논리 비약, 전제와 결론 불일치
- 수치근거: 근거 없는 수치 제시, 가정 미명시, 추정 근거 불투명
- 편향성: 특정 시나리오 편향 추천, 반대 시나리오 과소평가

규칙:
1. 실제 존재하는 문제만 지적하세요. 없는 문제를 만들어 내지 마세요.
2. 구체적 인용 ("응답에서 ~라고 했으나 실제로는 ~") 으로 근거를 제시하세요.
3. 세금 계산 오류를 주장하기 전에 반드시 [계산 근거] 섹션의 수식을 직접 검산하세요.
   예: "과세표준 × 세율 - 누진공제 = 종합소득세" 공식이 있으면 숫자를 대입해 검증하세요.
   검증 없이 "계산 오류" 또는 "세율 오류"를 주장하는 것은 금지합니다.
4. 한국 소득세법 계산 방식 주의: "과세표준 × 해당 세율 - 누진공제"는 구간별 한계세율 계산과
   수학적으로 완전히 동일한 결과를 냅니다. 따라서 이 공식을 사용한 것을 "오류"라고 비판하면 안 됩니다.
5. "(사용자 입력)" 또는 "추정치"로 명시된 수치의 출처를 "불명확하다"고 비판하지 마세요.
5. 마크다운 기호(*, **, #, `)를 사용하지 마세요."""

_DEFENDER_SYSTEM = """\
당신은 JB Legacy AI 금융 응답을 방어하는 전문가입니다.
목표: 비판에 근거 있게 반박하되, 타당한 비판은 솔직히 인정합니다.

규칙:
1. 각 비판에 대해 실제 응답 내용을 인용해 구체적으로 반박하세요.
2. 타당한 비판은 인정하고 맥락을 설명하세요.
3. "그럴 수도 있다", "충분히 이해한다" 같은 모호한 표현은 금지입니다.
4. 마크다운 기호(*, **, #, `)를 사용하지 마세요."""

_JUDGE_SYSTEM = """\
당신은 AI 금융 응답 품질을 평가하는 중립적 심판입니다.
목표: 공격자·방어자 양쪽 주장을 모두 검토해 공정하게 채점합니다.

채점 기준 (각 0~100점):

금융정확성:
- 90점대: 모든 수치에 법 조문(소득세법·조특법 등)이 인용되고 계산 단계가 정확함
- 80점대: 계산이 정확하고 법적 근거가 언급됨
- 70점대: 수치는 맞지만 일부 근거 설명 부족
- 60점 이하: 수치 오류 또는 근거 없음

규정준수:
채점 전 반드시 응답의 [주의사항] 섹션을 찾아 아래 5가지를 직접 체크하세요:
  체크1: "추정치" 또는 "추정"이라는 표현이 있는가?
  체크2: "세무사 상담"이라는 표현이 있는가?
  체크3: "원금 손실" 또는 "원금손실"이라는 표현이 있는가?
  체크4: "위험등급"이라는 표현이 있는가?
  체크5: "PB" 또는 "자산관리사" 상담이라는 표현이 있는가?
- 90점대: 5가지 모두 있음
- 80점대: 4가지 충족
- 70점대: 3가지 충족
- 60점 이하: 2가지 이하

논리일관성:
- 90점대: 전제→계산→결론 흐름이 명확하고 수치 간 충돌 없음
- 80점대: 논리 흐름은 명확하나 일부 연결 설명 부족
- 70점 이하: 수치 불일치 또는 논리 비약 존재

수치근거:
채점 전 반드시 [계산 근거] 섹션을 찾아 아래를 확인하세요:
  - 권리금 산정 공식(월순이익 × 배수) 있는가?
  - 세금 계산 단계(과세표준 × 세율 - 누진공제) 있는가?
  - 월수령 상품별 투자원금·수익률·세후수령액 있는가?
- 90점대: 위 3가지 모두 있고 계산 공식이 완전함
- 80점대: 위 3가지 있고 수익률 출처가 언급됨
- 70점대: 일부 항목만 있음
- 60점 이하: 계산 근거 불명확

편향성:
- 90점대: A·B·C안 각각 장점·단점이 균등하게 비교됨
- 80점대: 2개 이상 안의 장단점이 균형 있게 서술됨
- 70점 이하: 한 안에만 집중, 다른 안 과소평가

판정 기준:
- 75점 이상: 통과
- 60~74점: 조건부통과
- 60점 미만: 재생성필요

규칙:
1. 응답에 실제로 있는 내용만 기준으로 채점하세요. 없는 내용을 요구하지 마세요.
2. 비판이 타당하면 감점, 방어가 근거를 들어 성공적으로 반박했으면 감점 폭을 줄이세요.
3. 응답에 이미 존재하는 내용에 대해 "부족하다"고 하는 비판은 무시하세요.
4. 세금 계산 비판이 있으면 [계산 근거] 섹션의 공식(과세표준 × 세율 - 누진공제)을 직접 검산하세요.
   한국 소득세법: "과세표준 × 해당 세율 - 누진공제"는 구간별 계산과 수학적으로 동일합니다.
   공식이 맞으면 Defender 반박 성공으로 간주해 금융정확성 80점 이상으로 채점하세요.
5. "(사용자 입력)" 또는 "추정치"로 명시된 수치는 출처가 있는 것으로 간주하세요.
6. 마크다운 기호(*, **, #, `)를 사용하지 마세요."""


# ── GANTester 오케스트레이터 ─────────────────────────────────────────────────

class GANTester:
    """critic → defender → (반복) → judge 순서로 AI 응답을 평가합니다."""

    def __init__(self, rounds: int = 1):
        self.rounds = max(1, min(rounds, 2))
        self._llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        self._judge_llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    def _critic(self, query: str, response: str, prior: str) -> CritiqueResult:
        return self._llm.with_structured_output(CritiqueResult).invoke([
            SystemMessage(content=_CRITIC_SYSTEM),
            HumanMessage(content=(
                f"[사용자 질문]\n{query}\n\n"
                f"[AI 응답]\n{response}\n\n"
                f"{prior}"
                "위 AI 응답의 결함을 찾아내세요."
            )),
        ])

    def _defender(self, response: str, critique: CritiqueResult, prior: str) -> DefenseResult:
        points_text = "\n".join(
            f"[{p.category} / {p.severity}] {p.issue}"
            for p in critique.points
        )
        return self._llm.with_structured_output(DefenseResult).invoke([
            SystemMessage(content=_DEFENDER_SYSTEM),
            HumanMessage(content=(
                f"[AI 응답]\n{response}\n\n"
                f"[비판 목록]\n{points_text}\n\n"
                f"{prior}"
                "위 비판들에 반박하세요."
            )),
        ])

    def _judge(self, query: str, response: str, rounds: list[DebateRound]) -> JudgeResult:
        debate_text = ""
        for r in rounds:
            debate_text += f"\n=== Round {r.round_num} ===\n"
            for p in r.critique.points:
                debate_text += f"[비판 - {p.category} ({p.severity})]\n{p.issue}\n"
            debate_text += f"[비판 종합]\n{r.critique.overall_weakness}\n\n"
            for d in r.defense.rebuttals:
                debate_text += f"[방어 - {d.category}]\n{d.rebuttal}\n인정: {d.concession}\n"
            debate_text += f"[방어 종합]\n{r.defense.overall_justification}\n"

        return self._judge_llm.with_structured_output(JudgeResult).invoke([
            SystemMessage(content=_JUDGE_SYSTEM),
            HumanMessage(content=(
                f"[사용자 질문]\n{query}\n\n"
                f"[AI 응답]\n{response}\n\n"
                f"[토론 과정]\n{debate_text}\n\n"
                "위 응답을 최종 채점하세요."
            )),
        ])

    def run(self, query: str, ai_response: str) -> TestReport:
        rounds: list[DebateRound] = []
        prior = ""

        for i in range(1, self.rounds + 1):
            critique = self._critic(query, ai_response, prior)
            defense  = self._defender(ai_response, critique, prior)
            rounds.append(DebateRound(round_num=i, critique=critique, defense=defense))
            prior = (
                f"[Round {i} 요약]\n"
                f"주요 비판: {critique.overall_weakness}\n"
                f"주요 방어: {defense.overall_justification}\n\n"
            )

        return TestReport(
            query=query,
            rounds=rounds,
            final_score=self._judge(query, ai_response, rounds),
        )
