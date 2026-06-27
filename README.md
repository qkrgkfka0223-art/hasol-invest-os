# HASOL Invest OS

HASOL Invest OS는 미국주식 이벤트 기반 1차 감지 엔진이다.

이 저장소는 매수 추천기가 아니다.  
목적은 감지 시점 이후 실제 돈이 추가 유입될 가능성이 있는 후보를 넓게 잡고, 웹 정밀검증 전 단계까지 압축하는 것이다.

## 현재 버전

```text
HASOL_DETECTOR_V1.2
상태: baseline detector
실행후보: 기본 잠금
웹검증: 필수
시트기록: 아직 자동연동 금지
```

## 역할 분리

```text
GitHub / code = 감지 엔진
Web = 뉴스·공시·현재가 정밀검증
HASOL = 시장 → 이벤트 → 축 → Top20/Top5 판단
Sheet = 01_PREDICTION / 02_RESULT / 03_MISSED / 04_LEARNING 외부뇌
Haram = 최종 승인
```

## v1.2 핵심 변화

1. `sample/live` 모드 분리
2. sample 결과는 `SAMPLE_ONLY_DO_NOT_TRADE`로 잠금
3. execution_candidates 기본 잠금
4. live 모드도 웹 검증 전 실행 판단 금지
5. `data_quality_status` 추가
6. `run_metadata.json` 생성
7. yfinance live-ready fetcher 추가
8. SPY/QQQ 5일 상대강도 계산 개선
9. market_cap / cap_bucket 기반 Top20 분산 유지

## 실행

샘플 구조 테스트:

```bash
python main.py --mode sample --output-dir output_v12_sample
```

라이브 감지 테스트:

```bash
python main.py --mode live --universe-csv universe_seed.csv --output-dir output_live --max-tickers 200
```

실행후보 잠금 해제는 기본 금지다. 꼭 필요할 때만:

```bash
python main.py --mode live --universe-csv universe_seed.csv --allow-execution-candidates
```

그래도 최종 실행은 웹 검증과 하람 승인 후에만 한다.

## 산출물

```text
raw_candidates.csv
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

## 원칙

```text
Top20 = 예측 후보
Top5 = 강한 시나리오 후보
execution_candidates = 실제 실행 가능 후보
```

Top5와 execution_candidates는 같지 않다.

## 다음 개발 순서

```text
v1.2 = baseline detector 고정
v1.3 = Top20 웹검증 보조 강화
v1.4 = SEC live scanner 확장
v2.0 = Sheet 기록 연동 검토
```

## 금지

```text
자동매매 금지
sample 결과 매수판단 금지
웹 검증 전 execution_candidate 확정 금지
시트 자동기록 조기연동 금지
```
