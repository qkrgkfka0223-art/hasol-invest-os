# HASOL Invest OS

HASOL Invest OS는 미국주식 이벤트 기반 1차 감지 엔진이다.

이 저장소는 매수 추천기가 아니다.  
목적은 감지 시점 이후 실제 돈이 추가 유입될 가능성이 있는 후보를 넓게 잡고, 웹 정밀검증 전 단계까지 압축하는 것이다.

## 현재 버전

```text
HASOL_DETECTOR_V1.4
상태: candidate-builder first detector
실행후보: 기본 잠금
웹검증: 필수
시트기록: GitHub output schema 확정 전 자동연동 금지
```

## 역할 분리

```text
GitHub / code = 후보수집·감지 엔진
Web = 뉴스·공시·현재가 정밀검증
HASOL = 시장 → 이벤트 → 축 → Top20/Top5 판단
Sheet = 01_PREDICTION / 02_RESULT / 03_MISSED / 04_LEARNING 외부뇌
User = 최종 승인
```

## v1.4 핵심 변화

v1.3은 가격/거래량 구조는 잡았지만 후보풀이 좁고 `event_tags = NONE`이 많았다.

v1.4는 먼저 후보수집 구조를 코드 안에 넣는다.

1. `candidate_builder.py` 추가
   - universe seed + source별 discovery candidates 통합
   - source_count / candidate_source / source_confidence 기록
2. source layer 추가
   - `source_price_movers.py`
   - `source_news_catalysts.py`
   - `source_earnings.py`
   - `source_biotech_fda.py`
3. discovery-only 원칙
   - 새 source 후보는 매수후보가 아니다
   - 웹검증 전 실행 금지
4. event-first scoring 강화
   - event_score
   - source_count_score
   - underreaction_score
   - bad_event_penalty
5. `web_validation_checklist.csv` 강화
   - candidate_source
   - source_confidence
   - candidate_reason
   - bad_event_hits
   - must_verify
6. execution 후보 조건 강화
   - event_tags 없는 후보 실행 제외
   - bad_event_flag 후보 실행 제외

## 실행

샘플 구조 테스트:

```bash
python main.py --mode sample --output-dir output_v14_sample
```

라이브 감지 테스트:

```bash
python main.py --mode live --universe-csv universe_seed.csv --output-dir output_live --max-tickers 200
```

외부 후보 CSV를 추가해 실행:

```bash
python main.py \
  --mode live \
  --universe-csv universe_seed.csv \
  --external-candidates-csv external_candidates.csv \
  --output-dir output_live \
  --max-tickers 300
```

seed source 없이 입력 CSV만 테스트:

```bash
python main.py --mode live --universe-csv universe_seed.csv --no-seed-sources
```

웹검증 후 파일 분리:

```bash
python -m hasol_detector.web_review_helper \
  --review-csv output_live/web_validation_checklist.csv \
  --output-dir output_reviewed
```

실행후보 잠금 해제는 기본 금지다. 꼭 필요할 때만:

```bash
python main.py --mode live --universe-csv universe_seed.csv --allow-execution-candidates
```

그래도 최종 실행은 웹 검증과 사용자 승인 후에만 한다.

## 산출물

```text
raw_candidates.csv
tagged_candidates.csv
scored_candidates.csv
filtered_candidates.csv
rejected_candidates.csv
top20_candidates.csv
top5_candidates.csv
execution_candidates.csv
web_validation_checklist.csv
prediction_row.csv
run_metadata.json
```

웹검증 후:

```text
validated_top20.csv
validated_top5.csv
rejected_after_web.csv
```

## 원칙

```text
raw_candidates = 수집 후보
Top20 = 볼 만한 후보
Top5 = 강한 예측 후보
execution_candidates = 실제 실행 가능 후보
```

Top5와 execution_candidates는 같지 않다.

`DISCOVERY_ONLY` 후보는 원문 검증 전 매수후보가 아니다.
