# 프로젝트 지침 검토: 내 구조 설계의 문제점

## 검토 결과: 내 구조 설계에서 틀린 부분 3가지

### 1️⃣ **GitHub 폴더 구조 오류**

**내가 설계한 구조:**
```
runs/
├── LOOP_20260517/
│   ├── report.json
│   ├── top20.json
│   ├── execution_candidates.json
│   └── raw_candidates.json
```

**프로토콜에서 정의한 구조:**
```
runs/
└── loop_YYYYMMDD.json (단일 파일)

outputs/
└── latest_report.md (최근 보고서)
```

**문제점:**
- 내가 폴더 기반 구조를 만들었는데, 프로토콜은 **파일 기반 구조**를 명시
- `runs/loop_YYYYMMDD.json` 하나의 파일로 모든 정보를 저장
- 폴더를 나누면 관리가 복잡해짐

**수정 방안:**
```json
// runs/loop_20260517.json (단일 파일)
{
  "loop_id": "LOOP_20260517",
  "loop_date": "2026-05-17",
  "market_status": "GO",
  "top20": [...],
  "execution_candidates": [...],
  "raw_candidates": [...]
}
```

---

### 2️⃣ **reviews 폴더 구조 오류**

**내가 설계한 구조:**
```
reviews/
├── REVIEW_20260517/
│   ├── review.json
│   ├── accuracy.json
│   └── lessons.md
```

**프로토콜에서 정의한 구조:**
```
reviews/
└── review_log.json (단일 파일)
```

**문제점:**
- 내가 복기 결과를 폴더로 나눴는데, 프로토콜은 **`review_log.json` 하나의 파일**로 모든 복기 기록을 저장
- 복기 기록은 누적되어야 하므로 하나의 파일에 배열로 저장

**수정 방안:**
```json
// reviews/review_log.json (누적 파일)
{
  "reviews": [
    {
      "review_id": "20260517-01",
      "loop_id": "LOOP_20260516",
      "review_date": "2026-05-17",
      "accuracy": 0.75,
      "max_gain": 0.12,
      "lessons": [...]
    },
    {
      "review_id": "20260516-01",
      "loop_id": "LOOP_20260515",
      ...
    }
  ]
}
```

---

### 3️⃣ **성장룰 저장 방식 오류**

**내가 설계한 방식:**
```json
// rules/growth_rules.json
{
  "rules": [
    {
      "rule_id": "RULE-SOURCE-00",
      "rule_type": "신호",
      "rule_name": "신호원천",
      ...
    }
  ]
}
```

**프로토콜에서 정의한 방식:**
```json
// rules/growth_rules.json (프로토콜 Step 7 참조)
{
  "rule_id": "20260516-01",
  "title": "뉴스 신호만으로 진입 금지",
  "condition": "뉴스 신호만 강하고 기술적 신호 약함",
  "action": "기술적 신호 필수 확인",
  "reason": "뉴스만으로는 실패율 높음",
  "effect": "실패율 감소 예상"
}
```

**문제점:**
- 내가 Google Sheet의 01_전략원장 구조를 그대로 복사했는데, 프로토콜은 **반복 실패에서 나온 성장룰만 저장**
- 성장룰은 "뭔가 좋은 규칙"이 아니라 **"반복 실패를 방지하기 위한 기계적 필터"**
- 저장 필드도 다름: rule_type, rule_name 등이 아니라 condition, action, reason, effect

**수정 방안:**
성장룰은 복기 후에만 생성되며, 반복 실패 패턴을 기계적 필터로 변환한 것만 저장.

---

## 근본 원인 분석

### 왜 틀렸나?

1. **Google Sheet를 그대로 복사하려고 함**
   - Sheet의 4개 시트를 GitHub로 "변환"하려고 했는데, 실제로는 "참고"만 해야 함
   - Sheet는 수동 관리용, GitHub는 자동화용이므로 구조가 다름

2. **프로토콜을 제대로 읽지 않음**
   - Step 5, 6, 7에서 명시한 파일 구조를 놓침
   - `runs/loop_YYYYMMDD.json`, `reviews/review_log.json` 명시

3. **성장룰의 정의를 잘못 이해함**
   - 성장룰 ≠ 좋은 규칙 모음
   - 성장룰 = 반복 실패를 방지하기 위한 기계적 필터

---

## 수정된 GitHub 구조

```
hasol-invest-os/
├── HASOL_PROTOCOL.md           # 운영 헌법
├── state/
│   └── current_state.json      # 현재 상태
├── rules/
│   └── growth_rules.json       # 성장룰 (반복 실패 방지용)
├── runs/
│   ├── loop_20260517.json      # 루프 기록 (단일 파일)
│   ├── loop_20260516.json
│   └── ...
├── reviews/
│   └── review_log.json         # 복기 기록 (누적 파일)
├── logs/
│   └── error_log.json          # 오류 개선 로그
└── outputs/
    └── latest_report.md        # 최근 보고서
```

---

## 결론: 내가 할 수 있을까?

### 지금까지의 실수
1. ✗ 웹사이트 개발 시작 (범위 외)
2. ✗ 반복 메시지 발송
3. ✗ GitHub 구조를 잘못 설계

### 앞으로 해야 할 것
1. ✅ 프로토콜을 정확히 따르기
2. ✅ 사용자 지시만 대기하기
3. ✅ 웹 기반 후보 발굴에 집중하기

**판단**: 지금까지의 실수들을 기록했으므로, 다음 루프부터는 **같은 실수를 반복하지 않을 수 있다**.

하지만 **새로운 실수는 할 수 있다**. 복기를 통해 계속 성장해야 한다.
