# HASOL_DETECTOR_V1.3 RUN REPORT

## 왜 v1.3을 만들었나

최근 30일 급등 사례를 역복기한 결과, 기존 v1.2는 가격/거래량/시총 버킷 구조는 갖췄지만 다음 유형을 충분히 분리하지 못할 수 있었다.

```text
뉴스형 급등
SEC/지분구조형 급등
바이오 이벤트형 급등
유명 파트너 키워드형 급등
초저시총 detect-only 급등
```

## 반영한 실패 구조

### 1. SEC / 지분구조형

예시 구조:

```text
Form 3 / Form 4 / 13D / 13G / 8-K cluster
뉴스 없이 거래량 폭발
초저시총 또는 micro cap
```

추가 태그:

```text
SEC_CLUSTER
OWNERSHIP_CHANGE
COMPLIANCE_RECOVERY
```

### 2. micro/nano detect-only

초저시총은 제거가 아니라 분리한다.

```text
raw/top20 감지 허용
execution_candidates 기본 잠금
```

### 3. 바이오 이벤트 확장

FDA approval만 보는 구조를 수정했다.

추가 키워드:

```text
BLA accepted
resubmitted BLA
late-stage trial
met primary endpoint
exclusive rights
licensing deal
```

추가 태그:

```text
CLINICAL_SUCCESS
BLA_ACCEPTED
BIOTECH_LICENSE
```

### 4. 유명 파트너 키워드

소형주 뉴스에 강한 대형 파트너명이 붙을 때 감지 점수를 올린다.

```text
Starlink
SpaceX
NASA
AMD
NVIDIA
DoD
FDA
```

### 5. post-spike stage

감지와 추격을 분리하기 위해 stage를 추가했다.

```text
day1_spike
day2_continuation
day3_parabolic
post_climax_fade
base_or_quiet_rs
```

## 산출물 변화

`web_validation_checklist.csv`가 강화됐다.

새로 포함되는 필드:

```text
famous_partner_hits
biotech_event_hits
sec_cluster_flag
post_spike_stage
review_lock_reason
detect_only_reason
must_verify
risk_flags_to_check
decision_reason
```

## 웹검증 보조

새 파일:

```text
hasol_detector/web_review_helper.py
```

사용법:

```bash
python -m hasol_detector.web_review_helper \
  --review-csv output_live/web_validation_checklist.csv \
  --output-dir output_reviewed
```

생성 파일:

```text
validated_top20.csv
validated_top5.csv
rejected_after_web.csv
```

## 현재 제한

```text
SEC live scanner는 아직 hook 수준
live data 안정성 미검증
웹 검증은 여전히 수동/보조 방식
실행후보 자동확정 없음
```

## 다음 작업

```text
v1.4 = SEC live scanner 확장
v1.5 = market judgment module
v2.0 = Sheet write integration 검토
```
