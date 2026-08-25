# HASOL Invest OS

HASOL Invest OS는 미국주식의 **전체시장 deterministic Quant 계산 + 이벤트 후보 감지**를 담당하는 코드/실행 레이어다.

이 저장소는 매수 추천기가 아니다. 최종 투자판단은 HASOL이 하고 실제 자금집행은 사용자 승인 후에만 진행한다.

## 현재 구성

```text
HASOL_DETECTOR_V1.4
  = Web/price/event discovery 후보 생성

HASOL-QF-v1.0 / HASOL-QR-v1.0
  = historical SIP full-market features / deterministic rank / Quant Top50

상태
  Quant code + CI             VERIFIED
  Historical SIP scale        VERIFIED (98.718% broad-reference coverage)
  GitHub unattended SIP run   BLOCKED until Alpaca Actions secrets are configured
  Final production system     NOT_PRODUCTION
```

세부 검증상태: `docs/FULL_MARKET_QUANT_V1.md`

## 역할 분리

```text
Alpaca = MARKET SENSOR
Web = EVENT SENSOR
GitHub = deterministic full-market compute + code + tests + artifacts
HASOL = fusion + investment judgment
External Brain Sheet = official decision/review/learning memory
GPT automation = schedule + monitoring + orchestration
User = final capital-deployment approval
```

GitHub는 최종 판단하지 않는다. 시트도 최종 판단하지 않는다.

## Full-Market Quant

완료 세션의 canonical 시장데이터는 **historical consolidated SIP**다. IEX volume은 EOD 전체시장 canonical volume으로 사용하지 않는다.

```bash
python -m scripts.run_full_market_quant \
  --feed sip \
  --lookback-calendar-days 120 \
  --output-dir output_quant
```

주요 산출물:

```text
reference_universe.csv
reference_universe_meta.json
run_manifest.json
data_quality.json
universe_snapshot.csv
features.csv
full_rank.csv
quant_top50.csv
```

Integrity gate:

```text
market-data coverage >= 98%
Quant Top50 = exactly 50 valid candidates
input snapshot + commit + feature/rank spec lineage preserved
```

## Detector

샘플 구조 테스트:

```bash
python main.py --mode sample --output-dir output_v14_sample
```

라이브 discovery:

```bash
python main.py \
  --mode live \
  --universe-csv universe_seed.csv \
  --output-dir output_live \
  --max-tickers 300
```

`DISCOVERY_ONLY` 후보는 원문 검증 전 매수후보가 아니다.

## GitHub Actions

Full-market workflow:

```text
.github/workflows/full-market-quant.yml
```

Repository Actions secrets required for unattended Alpaca runs:

```text
ALPACA_API_KEY_ID
ALPACA_API_SECRET_KEY
```

Credentials must never be committed to source code, artifacts, Sheets, or chat logs.

## Prediction boundary

GitHub 산출물은 HASOL의 입력이다.

```text
Quant Top50
+
Web event candidates
+
expectations / premarket reaction / market regime
↓
HASOL fusion
↓
09:25 ET PREMARKET Top20 / Top5 freeze
```

현재는 전체 루프의 production gate를 통과하기 전이므로 자동매매 및 production prediction으로 간주하지 않는다.
