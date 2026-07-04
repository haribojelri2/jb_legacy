# JB Legacy 검증 하네스 (Harness Engineering)

이 프로젝트는 단발 프롬프트로 만든 결과물이 아니라, **계속 검증·고도화되도록 하네스를 프로젝트 안에 남긴** 서비스다. 아래 하네스로 개발 중 상시 검증하고, 수정할 때마다 관련 하네스를 재실행해 회귀를 막는다.

## 하네스 스킬 (`.claude/skills/`)

Claude Code에서 `/<스킬명>`으로 호출한다 (프로젝트 루트 = `jb_legacy/`에서 실행).

| 스킬 | 역할 | 언제 |
|---|---|---|
| `spec-consistency-check` | 발표 문서 ↔ 코드 정합성 (테스트 수·모델명·에이전트·수치) | 문서/코드 수정 후 |
| `mvp-scenario-test` | golden query를 전체 그래프에 태워 핵심 흐름 동작 검증 (+GAN 채점) | 그래프·프롬프트 수정 후, 시연 전 |
| `compliance-risk-review` | 금소법·개인정보·환각·책임소재 리스크 검토 | 응답·프롬프트·데이터 흐름 수정 후 |
| `agent-flow-review` | 판단·행동·검증/개선 루프 무결성 (배선·끊긴 루프·장애격리) | 그래프 구조 수정 후 |
| `improvement-backlog` | 본선 고도화 항목 스캔·우선순위화 → `IMPROVEMENT_BACKLOG.md` | 고도화 계획 점검 시 |

## 코드에 내장된 검증 루프 (런타임 하네스)

하네스는 개발 도구뿐 아니라 런타임에도 작동한다 — 평가기준 3의 "판단·행동·검증/개선" 구조:

1. **ComplianceGuard 이중 검수** (`agents/compliance.py`) — 결정론 수치 대조(룰 엔진, `verify_numbers`) + LLM 금소법 문구 검수. 미통과 시 지적사항 주입 재생성(최대 3회).
2. **GAN 적대 검증** (`agents/gan_tester.py`) — Critic·Defender·Judge 3-LLM 토론 채점. `GAN_AUTO=1`이면 그래프 내 자동 실행, '재생성필요' 판정 시 개선 지시 주입 재생성(최대 1회). UI 'AI 검증' 탭에서 수동 실행·전후 점수 비교.
3. **goal-seek 역산** (`tools/monte_carlo.py` `solve_target_monthly`) — 생존확률 목표 미달 시 지속가능 생활비를 이분 탐색으로 역산해 개선안 자동 제시.
4. **회귀 평가 하네스** (`eval/run_eval.py`) — golden query를 그래프+GAN 채점으로 회귀 게이트(`--gate`).
5. **관측성** (`graph.py`) — `JB_LOG=1`로 노드별 지연·재시도·검수 결과 구조화 로깅, LangSmith 옵트인.

## 재사용

이 하네스는 주제·데이터에 독립적이다. 다른 AI Agent 서비스에도 `.claude/skills/`를 그대로 가져가 골든 질의·검증 항목만 교체해 재사용할 수 있다.
