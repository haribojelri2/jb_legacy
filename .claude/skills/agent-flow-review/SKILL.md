---
name: agent-flow-review
description: LangGraph 멀티에이전트의 "판단·행동·검증/개선" 루프 무결성을 점검한다. 에이전트가 그래프에 실제 배선됐는지, 검증 루프가 끊기지 않았는지, supervisor 판단이 실행에 반영되는지 확인한다. 그래프 구조·노드·엣지를 바꾼 뒤 실행한다.
---

# AI Agent 흐름 무결성 하네스

대회 평가기준 3의 핵심인 "판단 → 행동 → 검증/개선" 루프가 실제로 닫혀 있는지 검증한다. 과거에 이 루프가 곳곳에서 끊겨 있었다(검증기가 개선으로 안 이어짐, 에이전트가 그래프 밖 UI 헬퍼로만 존재, 판단이 실행에 반영 안 됨).

## 점검 항목

1. **에이전트 배선(orphan 탐지)**
   - `agents/` 디렉터리의 각 에이전트가 `graph.py`에 `add_node`로 등록됐는가, 아니면 `ui/app.py`에서만 직접 호출되는 UI 헬퍼인가
   - UI 헬퍼로만 존재하면 "멀티에이전트 오케스트레이션"이 아니라 대시보드 위젯 — 그래프 승격 후보

2. **판단이 실행에 반영되는가 (동적 라우팅)**
   - `graph.py`의 `_route_dispatch`가 `selected_agents`에 따라 노드를 선택 실행하는가 (정적 fan-out + self-skip 가드가 남아있지 않은가)
   - supervisor 선택이 스트림 이벤트·실행 비용에 실제 반영되는지

3. **검증/개선 루프가 닫혀 있는가**
   - compliance FAIL → `compliance_feedback` 주입 → synthesizer 재생성 경로 (`graph.py` _route_compliance → synthesizer)
   - GAN '재생성필요' → `gan_regen_needed` → synthesizer 재생성 (`agents/gan_tester.py` gan_review_agent, GAN_AUTO 모드)
   - goal-seek: 생존확률 미달 시 지속가능 생활비 역산이 결과에 실림 (`agents/post_exit_wm.py`)
   - 검증 결과가 "표시만" 되고 개선 액션으로 이어지지 않는 반쪽 루프가 없는가

4. **장애 격리**
   - LLM 호출에 `max_retries`가 걸려 있는가 (`agents/llm.py`) — 시연 중 API 블립 1회로 그래프 전체가 죽지 않도록
   - 라우팅 파싱 실패 시 안전한 폴백이 있는가 (supervisor 구조화 출력 + 예외 격리)

5. **종료 조건**
   - 재시도 루프(compliance retry, GAN retry)에 상한이 있어 무한 루프가 불가능한가

## 검증 방법

`JB_LOG=1`로 E2E를 실행하면 노드별 진입/지연/재시도/검수 결과가 로깅되므로, 실제 실행 경로가 설계와 일치하는지 로그로 확인:
```python
import os; os.environ["JB_LOG"] = "1"
from graph import run_query
run_query(user_id="lee_sajang", query="...")
```

## 출력

루프별 상태표: `루프 | 배선 상태 | 실제 동작 여부 | 끊긴 지점`. 끊긴 루프가 있으면 어디서 개선 액션이 누락됐는지 명시.
