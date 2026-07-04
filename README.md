# JB Legacy — 자영업자 엑시트 AI 에이전트

평생 일군 가게를 가장 명예롭게 물려주거나(승계) 가장 안전하게 매각하여
완벽한 은퇴를 돕는 자영업자 전용 LifeLong WM 멀티에이전트 시스템.
JB금융그룹 Fin AI Challenge 출품 데모.

LangGraph 멀티에이전트가 "판단 → 행동 → 검증/개선"으로 동작하며,
추론 LLM은 Anthropic Claude(`claude-opus-4-8`)를 사용한다(팩토리 라우팅으로 GPT 즉시 전환 가능).

## 빠른 시작

```bash
# 1. 의존성 설치 (Python 3.14 기준)
pip install -r requirements.txt

# 2. API 키 설정
copy .env.example .env
#   .env에 ANTHROPIC_API_KEY(추론) + OPENAI_API_KEY(임베딩·STT·TTS) 입력
#   (선택) MODEL_FAST=claude-haiku-4-5 로 라우팅·변환을 빠르게

# 3. 실행 (포트 8502 — E2E 테스트가 이 포트를 가정)
streamlit run ui/app.py --server.port 8502
```

SQLite mock DB(`data/mock_data.db`)와 ChromaDB 벡터스토어(`rag/chroma_db`)는
첫 실행 시 자동 생성됩니다.

## 파이프라인 (LangGraph)

```
supervisor → profiler
    ↓ clarification_needed?
    YES → END  (사용자에게 추가 질문 반환)
    NO  ↓ dispatch — 동적 fan-out(selected_agents 노드만 실제 실행)
BusinessValuation ─┐
TaxSuccession ─────┤
PostExitWM ────────┼→ synthesizer → slow_ui → compliance ─┐검수
Negotiation ───────┤                    ↑ retry(재생성)   │
EarlyWarning ──────┘                     └────────────────┘
                                         compliance pass ↓
                              gan_review(적대 검증, GAN_AUTO) ─┐
                                    ↑ 재생성필요               │
                              synthesizer ←───────────────────┘
                                         gan pass ↓
                              family_bridge → booking → END
```

- 진입점: `graph.py` → `run_query()` / `stream_query()`
- **동적 라우팅**: `dispatch`가 supervisor 선택 노드만 실행(conditional edges)
- **이중 검증/개선 루프**: (1) ComplianceGuard 금소법+수치 대조 검수, (2) GAN 적대 검증
  (Critic·Defender·Judge). 미통과 시 지적사항 주입 재생성.
- 병렬 fan-out 노드끼리는 state를 공유할 수 없으므로, 권리금 등 공통 수치는
  `tools/calculators.py`의 `resolve_business_value()`를 각자 호출해 단일 출처를 보장합니다.
- 체크포인터: SqliteSaver (`jb_legacy_memory.db`, thread_id별 영속화)

## 3축 분석 프레임

| 시나리오 | 의미 | 축 |
|---|---|---|
| A. 완전 매각 | 권리금 현금화 + 운용 포트폴리오 | 부모 안정 |
| B. 완전 승계 | 자녀에게 가업 이전 + 자문료 | 가족 자산 지속 |
| C. 절충안 | 권리금 50% + 지분 50% 승계 | 균형 |
| D. 가족 합의안 | 자녀가 제안한 협상 조건 기반 | 협상 (Negotiation 에이전트) |

## 데모 시나리오

1. Step 1에서 **이사장** (62세, 전주, 한정식 30년, 월순이익 450만) 선택
2. "가게 정리하고 은퇴하면 어떻게 되나요?" 입력 → A/B/C 비교 분석
3. "딸이 70% 승계에 자문료 20%를 제안하면?" → D안(가족 합의안) 생성
4. "상권이 하락세면 어떻게 돼?" → what-if 재분석 + 변경 전후 비교
5. 우측 패널: 세금 비교 / 생존 확률(CPP 몬테카를로 + goal-seek 지속가능 생활비 역산) /
   **AI 검증**(GAN 채점·개선 전후 비교) / 조기경보 / 청년 매칭 /
   **거래 안심**(소비흐름 + 이상거래 탐지 + 가족 알림) / PDF 리포트 다운로드
6. 시니어 모드(이사장): 음성 입력(STT)으로 말로 질문 + TTS 음성 브리핑

## 테스트 · 검증 하네스

```bash
# 통합 하네스 (한 명령 — 단위 테스트 + 문서-코드 정합성 + Agent 배선)
python harness_check.py
python harness_check.py --scenario   # + 대표 시나리오 그래프 스모크 (LLM)

# 단위 테스트만 (서버·API 키 불필요)
python -m pytest tests/ --ignore=tests/test_ui.py -q

# E2E (Playwright — 포트 8502에 앱이 떠 있어야 함)
python -m pytest tests/test_ui.py -v
```

프로젝트를 상시 검증·고도화하는 하네스 스킬(`.claude/skills/`)이 있다. `jb_legacy/`에서
Claude Code로 `/spec-consistency-check`, `/mvp-scenario-test`, `/compliance-risk-review`,
`/agent-flow-review`, `/improvement-backlog`, `/harness-all`을 호출한다. 상세는 `HARNESS.md`.

## 디렉토리

```
graph.py           LangGraph 오케스트레이터 (run_query / stream_query)
harness_check.py   통합 검증 하네스 러너
agents/            에이전트 노드 (supervisor, synthesizer, compliance, gan_tester, monitoring …)
agents/llm.py      LLM 팩토리 (Claude/OpenAI 라우팅, tier·max_tokens)
tools/             순수 계산 (세금·권리금·현금흐름·몬테카를로·goal-seek·PDF)
data/              mock 페르소나, SQLite DB, JB 상품, 세법 문서
rag/               ChromaDB 세법 RAG (조문 청킹 + 출처 인용, OpenAI 임베딩)
ui/app.py          Streamlit UI (온보딩 → 채팅 + 분석 패널 + AI 검증 탭)
tests/             단위 테스트 + Playwright E2E
.claude/skills/    검증·고도화 하네스 스킬
```

## 문서

- `OVERVIEW.md` — 시스템 상세 (수치 기준표 + 고도화 이력)
- `HARNESS.md` — 검증·고도화 하네스 (개발-시 스킬 + 런타임 검증 루프)
- `기능명세서.md` — 기능 명세
- `MVP제안서.md` — 서비스 제안
- `JB_Fin_AI_Challenge_brief_v3.md` — 대회 기획 시점 브리프(구버전, 최신은 OVERVIEW.md 기준)
