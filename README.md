# JB Legacy — 자영업자 엑시트 AI 에이전트

평생 일군 가게를 가장 명예롭게 물려주거나(승계) 가장 안전하게 매각하여
완벽한 은퇴를 돕는 자영업자 전용 LifeLong WM 멀티에이전트 시스템.
JB금융그룹 Fin AI Challenge 출품 데모.

## 빠른 시작

```bash
# 1. 의존성 설치 (Python 3.14 기준)
pip install -r requirements.txt

# 2. API 키 설정
copy .env.example .env      # 후 .env에 실제 OPENAI_API_KEY 입력

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
    NO  ↓ (병렬 fan-out — selected_agents 기반 선택 실행)
BusinessValuation ─┐
TaxSuccession ─────┤→ synthesizer → slow_ui → compliance
PostExitWM ────────┤      ↓ retry?
Negotiation ───────┘  YES → synthesizer   NO → family_bridge → booking → END
```

- 진입점: `graph.py` → `run_query()` / `stream_query()`
- 병렬 fan-out 노드끼리는 state를 공유할 수 없으므로, 형제 결과가 필요한
  에이전트는 `tools/calculators.py`의 계산 함수를 직접 호출합니다.
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
5. 우측 패널: 세금 비교 / 생존 확률(CPP 의료비 쇼크 몬테카를로) /
   조기경보 / 청년 매칭 / **거래 안심**(소비흐름 + 이상거래 탐지 + 가족 알림) /
   PDF 리포트 다운로드
6. 시니어 모드(이사장): 음성 입력(STT)으로 말로 질문 + TTS 음성 브리핑

## 테스트

```bash
# 단위 테스트 (서버 불필요, API 키 불필요)
python -m pytest tests/test_calculators.py -v

# E2E (Playwright — 포트 8502에 앱이 떠 있어야 함)
python -m pytest tests/test_ui.py -v
```

## 디렉토리

```
graph.py           LangGraph 오케스트레이터 (run_query / stream_query)
agents/            에이전트 노드 (supervisor, synthesizer, compliance …)
tools/             순수 계산 (세금·권리금·현금흐름·몬테카를로·PDF)
data/              mock 페르소나, SQLite DB, JB 상품, 세법 문서
rag/               ChromaDB 세법 RAG (text-embedding-3-small)
ui/app.py          Streamlit UI (온보딩 → 채팅 + 분석 패널)
tests/             단위 테스트 + Playwright E2E
```

## 문서

- `OVERVIEW.md` — 시스템 상세 (수치 기준표 포함)
- `기능명세서.md` — MVP v1.0 기능 명세
- `MVP제안서.md` — 서비스 제안
- `JB_Fin_AI_Challenge_brief_v3.md` — 대회 출품 기준
