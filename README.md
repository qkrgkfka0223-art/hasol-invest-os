# HASOL Invest OS

HASOL Invest OS는 미국주식 이벤트 기반 1차 감지 엔진이다.

이 저장소는 매수 추천기가 아니다.  
목적은 감지 시점 이후 실제 돈이 추가 유입될 가능성이 있는 후보를 넓게 잡고, 웹 정밀검증 전 단계까지 압축하는 것이다.

## 현재 버전

```text
HASOL_DETECTOR_V1.4
상태: baseline detector + Top20 review helper + move_phase classifier
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
User = 최종 승인
```

## v1.4 핵심 변화

v1.4는 스크린샷형 급등주를 뒤늦게 따라붙지 않기 위해 `move_phase`를 추가했다.

```text
EARLY_SIGNAL = +8~35% 구간, 거래량 확장, 과열 없음
GAP_EARLY_SIGNAL = 갭 초기, VWAP/전일고점 확인 필요
QUIET_RS_VOLUME_EXPANSION = 가격 급등 전 거래량 확장
HOT_SIGNAL_WATCH_ONLY = +35~80%, 관찰/눌림 필요
CLIMAX_REVIEW_ONLY = +80% 이상 또는 포물선/클라이맥스
POST_CLIMAX_FADE = 이전 급등 후 붕괴/반락
BASE_OR_QUIET_RS = 아직 초기 후보 또는 조용한 상대강도
```

### v1.3에서 유지되는 기능

1. `SEC_CLUSTER` 감지
   - Form 3 / Form 4 / 13D / 13G / 8-K 묶음 감지
2. micro/nano 감지전용 분리
   - 초저시총도 Top20 감지는 허용
   - execution_candidates는 기본 잠금
3. 바이오 이벤트 확장
   - BLA accepted
   - resubmitted BLA
   - late-stage trial
   - met primary endpoint
   - exclusive rights / licensing deal
4. 유명 파트너 키워드
   - Starlink / SpaceX / NASA / AMD / NVIDIA / DoD / FDA 등
5. post-spike stage 분류
   - day1_spike
   - day2_continuation
   - day3_parabolic
   - post_climax_fade
   - base_or_quiet_rs
6. `web_validation_checklist.csv` 강화
   - 왜 감지됐는지
   - 왜 잠겨야 하는지
   - 웹에서 무엇을 확인해야 하는지
7. `web_review_helper.py`
   - 검증 후 validated/rejected 파일 생성

## 실행

샘플 구조 테스트:

```bash
python main.py --mode sample --output-dir output_v14_sample
```

라이브 감지 테스트:

```bash
python main.py --mode live --universe-csv universe_seed.csv --output-dir output_live --max-tickers 200
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
Top20 = 웹검증 대상
Top5 = 강한 시나리오 후보
execution_candidates = 실제 실행 검토 후보
```

Top5와 execution_candidates는 같지 않다.

## 다음 개발 순서

```text
v1.4 = move_phase / execution_phase_ok / 과열 잠금 강화
v1.5 = market judgment module
v1.6 = missed mover retro 자동화
v2.0 = Sheet 기록 연동 검토
```

## 금지

```text
자동매매 금지
sample 결과 매수판단 금지
웹 검증 전 execution_candidate 확정 금지
micro/nano 실행후보 자동확정 금지
시트 자동기록 조기연동 금지
HOT_SIGNAL/CLIMAX 추격 매수후보 표현 금지
```
