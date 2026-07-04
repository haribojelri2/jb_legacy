---
name: mvp-scenario-test
description: 대표 사용자 질문(golden query)을 실제 LangGraph에 태워 MVP 핵심 흐름이 끝까지 동작하는지 검증한다. 그래프·에이전트·프롬프트·라우팅을 수정한 뒤, 또는 시연·발표 직전 리허설로 실행한다. 실제 LLM을 호출하므로 API 키와 수 분의 시간이 필요하다.
---

# MVP 시나리오 회귀 테스트 하네스

단위 테스트가 커버하지 못하는 것 — 실제 LLM이 붙은 전체 그래프가 대표 질문에 대해 끝까지 정상 응답을 내는지 — 를 검증한다.

## 실행

1. **환경 확인**: `jb_legacy/.env`에 `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`가 있는지 확인 (없으면 중단하고 사용자에게 알림).

2. **평가 하네스 실행**:
   ```
   python -m eval.run_eval --label smoke
   ```
   golden query 4종(종합 상담 / 증여세 단독 / 노후 월수령 / 권리금)을 그래프에 태우고, GAN 채점까지 수행해 `eval/results/smoke.json`에 저장한다. 회귀 게이트가 필요하면 `--gate 70`(평균 총점 미달 시 exit 1).

3. **결과 판독** — 각 질의마다 확인:
   - `selected_agents`가 질문 성격에 맞는가 (단독 질문에 코어 3개가 다 도는 과잉 라우팅은 없는가)
   - `compliance_passed`가 True인가
   - GAN `total_score` / `verdict` (조건부통과 이하면 개선 여지)
   - `response_len`이 비정상적으로 짧지 않은가 (빈 응답·조기 종료 감지)

4. **직접 시연 검증이 필요하면** 전체 흐름을 1회 수동 실행:
   ```python
   from graph import run_query
   state = run_query(user_id="lee_sajang", query="폐업할지 승계할지 고민입니다. 세금이랑 노후 생활비까지 분석해주세요.")
   ```
   `final_response`에 마크다운 유출(`**`, `##`)이 없고 `[주의사항]` 면책이 붙었는지, `retirement_portfolio.monte_carlo_comparison`에 goal_seek가 채워졌는지 확인.

## 시연 리허설 체크리스트

- 추천 시나리오(A/B/C)는 실행마다 달라질 수 있음 — 발표 대본이 특정 안 기준이면 사전 확인
- `GAN_AUTO=1`을 켜면 응답당 +60~90초 — 시연 시간 배분 확인, 또는 UI 'AI 검증' 탭 버튼 방식으로 시연
- 시연장 네트워크 블립 대비 발표 직전 워밍업 1회

## 출력

질의별 결과 표 + 실패/경고 항목. 회귀(직전 `eval/results/` 대비 점수 하락)가 있으면 명시.
