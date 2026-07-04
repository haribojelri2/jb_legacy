---
name: harness-all
description: 모든 검증 하네스를 한 번에 실행한다 — 기계적 검사(단위 테스트·정합성·배선)를 harness_check.py로 돌린 뒤, LLM 추론이 필요한 리뷰(준법 리스크·Agent 흐름·고도화 백로그)를 순차 수행해 통합 리포트를 낸다. 대규모 수정 후 또는 발표·제출 직전 전체 점검용.
---

# 통합 하네스 실행

프로젝트의 모든 하네스를 한 번에 돌려 전체 상태를 점검한다.

## 실행 순서

1. **기계적 검사 (한 명령, 수초)** — 먼저 실행:
   ```
   python harness_check.py
   ```
   단위 테스트 전체 + 문서-코드 정합성(테스트 수·모델·골든 수치) + Agent 배선/검증 루프 무결성을 한 번에 검사하고 `N/M 통과` 대시보드를 낸다.
   대표 시나리오 그래프 스모크까지 포함하려면(LLM·수분·API 키 필요):
   ```
   python harness_check.py --scenario
   ```

2. **LLM 추론 리뷰 (순차)** — `harness_check.py`가 잡지 못하는 판단성 검토를 각 스킬 절차대로 수행:
   - `compliance-risk-review` — 금소법·개인정보·환각·책임소재 리스크
   - `agent-flow-review` — 판단·행동·검증/개선 루프의 논리적 무결성(배선 넘어 의미 검토)
   - `improvement-backlog` — 본선 고도화 항목 우선순위화 → `IMPROVEMENT_BACKLOG.md` 갱신

   (`spec-consistency-check`·기계 배선은 1단계에 이미 포함되므로 중복 실행하지 않는다. 시나리오 동작은 `mvp-scenario-test` 또는 `--scenario`로 커버.)

## 출력

통합 리포트:
- **자동 검사 결과**: `harness_check.py`의 PASS/FAIL 대시보드 그대로
- **리스크·흐름 리뷰**: 심각도순 발견 사항
- **고도화 백로그**: 우선순위 상위 항목 요약 (전체는 IMPROVEMENT_BACKLOG.md)
- **종합 판정**: 발표/제출 준비 상태 한 줄 요약

코드·문서를 임의 수정하지 않는다 — 발견 사항을 보고하고, 수정은 사용자 확인 후.
