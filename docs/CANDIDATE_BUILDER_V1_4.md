# HASOL Detector v1.4 Candidate Builder

## 결론

v1.4의 목적은 종목 추천이 아니라 후보수집 구조 확정이다.

```text
웹/SEC/뉴스/실적/FDA/가격 후보
→ raw_candidates
→ event_tags / axis_tags
→ risk lock
→ Top20
→ Top5
→ execution_candidates
```

## 이번 패치의 핵심

기존 v1.3은 `universe_seed.csv` 중심이었다.

v1.4는 `candidate_builder.py`가 여러 discovery source를 합친 뒤 가격/거래량/이벤트 점수화로 넘긴다.

## 추가된 source layer

```text
source_price_movers.py
source_news_catalysts.py
source_earnings.py
source_biotech_fda.py
```

각 source는 매수 리스트가 아니다.

모든 source row는 기본적으로 `DISCOVERY_ONLY`이며, 웹검증 전 실행 금지다.

## 새 흐름

```text
candidate_builder.build_candidate_pool()
→ ticker pool 확장
→ yfinance/sample price fetch
→ attach_candidate_context()
→ build_features()
→ tag_catalysts()
→ add_cap_bucket()
→ add_post_spike_stage()
→ score_candidates()
→ apply_kill_rules()
→ Top20 / Top5 / execution 분리
```

## v1.4 성공 기준

```text
raw_candidates 100개 이상
Top20에 candidate_source/source_count/source_confidence 포함
web_validation_checklist에 검증 이유 포함
execution_candidates는 계속 lock 기본값
```

## v1.4 한계

이 버전은 실제 웹 300~500개 자동 크롤러 완성본이 아니다.

정확한 위치:

```text
v1.4 = 후보수집 파이프라인 골격 + seed discovery sources
v1.5 = 실제 후보 300~500개 확장
v1.6 = SEC/news/FDA live ingestion 강화
```

## 금지

```text
DISCOVERY_ONLY 후보를 실행후보처럼 말하지 않는다.
Top5를 execution_candidates처럼 말하지 않는다.
웹검증 전에는 매수 판단 금지.
```
