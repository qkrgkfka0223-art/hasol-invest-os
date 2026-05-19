# HASOL 외부뇌 구조 (GitHub 기반)

**최종 수정**: 2026-05-19  
**목표**: Google Sheet 의존 제거 → GitHub 유일 기억 저장소

---

## 1. 디렉토리 구조

```
hasol-invest-os/
├── README.md                    # 프로젝트 개요
├── EXTERNAL_BRAIN_STRUCTURE.md  # 이 파일 (외부뇌 구조)
├── docs/
│   ├── HASOL_PROTOCOL.md        # 운영 헌법
│   ├── EXECUTION_GUIDE.md       # 루프 실행 가이드 (Step 1~8)
│   ├── REVIEW_GUIDE.md          # 루프 복기 가이드 (Step 1~7)
│   ├── SAVE_GUIDE.md            # 루프 기록 가이드 (Step 1~5)
│   └── TIME_SCHEDULE.md         # 루프 실행 시간표
├── state/
│   ├── current_state.json       # 현재 루프 상태
│   └── loop_history.json        # 모든 루프 히스토리
├── rules/
│   ├── growth_rules.md          # 성장룰 (누적)
│   └── filters/
│       ├── hard_filters.json    # Hard Filter 규칙
│       ├── soft_filters.json    # Soft Filter 규칙
│       └── scoring_rules.json   # 점수 계산 규칙
├── runs/
│   ├── LOOP_20260519_01/
│   │   ├── loop_report.md       # 루프 실행 보고서
│   │   ├── loop_data.json       # 루프 데이터 (Top20, Top3)
│   │   ├── market_judgment.json # 시장 판정
│   │   └── execution_log.md     # 실행 로그
│   ├── REVIEW_20260519_01/
│   │   ├── review_report.md     # 복기 보고서
│   │   ├── review_data.json     # 복기 데이터 (성과 분석)
│   │   └── growth_rules_new.md  # 새로 생성된 성장룰
│   └── ...
├── logs/
│   ├── error_log.json           # 에러 로그
│   ├── execution_log.json       # 실행 로그
│   └── performance_log.json     # 성과 로그
├── analysis/
│   ├── top20_analysis.json      # Top20 분석 결과
│   ├── top3_analysis.json       # Top3 분석 결과
│   ├── false_negatives.md       # 놓친 대어 분석
│   └── success_rate.json        # 성공률 통계
└── .gitignore
```

---

## 2. 루프 실행 데이터 구조

### 2.1 current_state.json
```json
{
  "current_loop_id": "LOOP_20260519_01",
  "current_loop_status": "루프준비 완료",
  "market_judgment": "GO",
  "market_judgment_time": "2026-05-19T21:30:00Z",
  "top20_count": 20,
  "top3_count": 3,
  "execution_candidates": 1,
  "last_update": "2026-05-19T21:35:00Z",
  "next_action": "루프시작",
  "applied_growth_rules": [
    "Rule 20260514-01",
    "Rule 20260514-02",
    "Rule 20260512-02"
  ]
}
```

### 2.2 loop_data.json (루프별)
```json
{
  "loop_id": "LOOP_20260519_01",
  "loop_start_time": "2026-05-19T21:30:00Z",
  "market_judgment": "GO",
  "market_data": {
    "spy_change": "+0.5%",
    "qqq_change": "+1.2%",
    "vix": 15.5,
    "10y_yield": 4.25
  },
  "top20": [
    {
      "rank": 1,
      "ticker": "UBER",
      "company": "Uber Technologies",
      "sector": "Technology",
      "detection_price": 75.50,
      "target_price_1": 83.05,
      "target_price_2": 90.60,
      "invalid_price": 67.95,
      "score": 85,
      "confidence": 88,
      "success_rate": 78,
      "accuracy": 86,
      "upside_probability": 75.45,
      "news_signal": "New partnership announcement",
      "news_strength": 5,
      "technical_signal": "Volume surge 350%",
      "technical_strength": 4,
      "institutional_signal": "Insider buying",
      "institutional_strength": 4,
      "sector_momentum": "Strong",
      "market_cap": "150B",
      "selected": false
    },
    ...
  ],
  "top3": [
    {
      "rank": 1,
      "ticker": "UBER",
      "company": "Uber Technologies",
      "detection_price": 75.50,
      "target_price_1": 83.05,
      "target_price_2": 90.60,
      "invalid_price": 67.95,
      "r_value": 1.5,
      "bull_case": "Partnership expansion + earnings growth",
      "bear_case_1": "Regulatory headwind",
      "bear_case_1_rebuttal": "Regulatory environment improving",
      "bear_case_2": "Valuation compression",
      "bear_case_2_rebuttal": "Growth justifies valuation",
      "selected": true,
      "execution_status": "PENDING"
    },
    ...
  ],
  "execution_candidates": [
    {
      "rank": 1,
      "ticker": "UBER",
      "selected": true,
      "entry_price": 75.50,
      "target_price_1": 83.05,
      "target_price_2": 90.60,
      "stop_loss": 67.95,
      "execution_time": "2026-05-19T21:35:00Z",
      "execution_status": "PENDING"
    }
  ]
}
```

### 2.3 review_data.json (복기별)
```json
{
  "review_id": "REVIEW_20260519_01",
  "loop_id": "LOOP_20260519_01",
  "review_date": "2026-05-22",
  "review_days": 3,
  "top3_performance": [
    {
      "rank": 1,
      "ticker": "UBER",
      "entry_price": 75.50,
      "current_price": 82.50,
      "max_price": 85.00,
      "min_price": 74.00,
      "return": 9.27,
      "status": "LOSS",
      "success": false
    },
    ...
  ],
  "top20_performance": [
    {
      "rank": 5,
      "ticker": "NVDA",
      "entry_price": 120.00,
      "current_price": 135.00,
      "max_price": 138.00,
      "min_price": 119.00,
      "return": 12.5,
      "status": "WIN",
      "success": true
    },
    ...
  ],
  "analysis": {
    "top3_success_count": 2,
    "top3_success_rate": 66.67,
    "top20_success_count": 8,
    "top20_success_rate": 40,
    "false_negatives": ["NVDA", "MSFT"],
    "false_positives": ["INOD"],
    "root_cause": "뉴스 신호 강도 과대 평가",
    "new_growth_rules": [
      "Rule 20260519-01: 뉴스 신호 강도 재조정"
    ]
  }
}
```

---

## 3. 성장룰 관리

### 3.1 growth_rules.md 구조
```
# HASOL 성장룰 (누적)

## 루프별 성장룰 생성 기록

### LOOP_20260519_01 복기 결과
- Rule 20260519-01: 뉴스 신호 강도 조정
- Rule 20260519-02: 거래량 필터 강화
- Rule 20260519-03: 섹터 모멘텀 재평가

### LOOP_20260518_01 복기 결과
- Rule 20260518-01: 기관 수급 신호 우선
- Rule 20260518-02: 실적 발표 72시간 필터

...

## 현재 적용 중인 성장룰 (총 XX개)
- Rule 20260514-01~21 (프로토콜 v2.0)
- Rule 20260512-01~05 (초기 성장룰)
- Rule 20260518-01~02
- Rule 20260519-01~03
```

---

## 4. 루프 실행 흐름

### 4.1 루프준비 (Loop Preparation)
```
1. GitHub 읽기
   - current_state.json 읽기
   - growth_rules.md 읽기
   - 최근 루프 결과 확인

2. 성장룰 반영
   - 적용할 성장룰 목록 확인
   - 필터 규칙 로드
   - 점수 계산 규칙 로드

3. 현재 상태 확인
   - 최근 루프 ID
   - 최근 루프 결과
   - 적용할 성장룰 목록
```

### 4.2 루프시작 (Loop Start)
```
1. 웹 기반 후보 발굴
   - 뉴스 검색 (Google News, Yahoo Finance)
   - 실적 발표 확인
   - 신규 계약/파트너십 확인
   - 기술 뉴스 확인
   - 기관/내부자 거래 확인

2. Top20 압축
   - 뉴스 신호 점수 계산
   - 기술적 신호 점수 계산
   - 기관 수급 점수 계산
   - 섹터 모멘텀 점수 계산
   - 시총 규모 조정
   - Hard Filter 적용

3. 가격 검증
   - 감지가 확정 (오늘 개장가 또는 전일 종가)
   - 목표가/손절가 설정
   - R-Value 확인 (≥ 1.0)
   - 기술적 신호 재확인

4. Top3 선정
   - 상승 확률 Top3 선정
   - 하락 시나리오 2개 + 반박 근거 작성
   - 확신 없으면 0개 선정 고려

5. 시장판정
   - GO / SOFT_GO / NO_TRADE 판정
   - 판정 근거 기록

6. 루프 기록
   - loop_data.json 생성
   - loop_report.md 생성
   - GitHub 커밋
```

### 4.3 루프복기 (Loop Review)
```
1. 성과 측정
   - Top3 성과 분석
   - Top20 성과 분석
   - 성공/실패 판정 (10% 이상 = 성공)

2. 실패 원인 분석
   - "왜 틀렸는가?" 분석
   - "왜 놓쳤는가?" 분석
   - 기계적 차단/포착 룰 생성

3. 성장룰 생성
   - 새로운 성장룰 작성
   - growth_rules.md 업데이트
   - GitHub 커밋

4. 복기 기록
   - review_data.json 생성
   - review_report.md 생성
   - GitHub 커밋
```

---

## 5. 커밋 규칙

### 5.1 커밋 메시지 형식
```
[LOOP_YYYYMMDD_NN] 루프 실행 완료 - Top20: XX, Top3: XX, Market: GO/SOFT_GO/NO_TRADE

[REVIEW_YYYYMMDD_NN] 루프 복기 완료 - 성공률: XX%, 새 성장룰: XX개

[GROWTH_RULES] 성장룰 업데이트 - Rule YYYYMMDD-XX 추가
```

### 5.2 커밋 빈도
- 루프 실행 후: 즉시 커밋
- 루프 복기 후: 즉시 커밋
- 성장룰 생성 후: 즉시 커밋

---

## 6. 성장 메커니즘

### 6.1 루프별 성장
```
Loop 1-10: 80% 이상 목표
Loop 11-30: 85% 이상 목표
Loop 31+: 90% 이상 목표
```

### 6.2 성장룰 누적
- 매 루프마다 새로운 성장룰 생성
- 성장룰이 누적될수록 예측률 향상
- 반복 실패 패턴 제거

### 6.3 성과 추적
- performance_log.json: 루프별 성공률 기록
- success_rate.json: 누적 성공률 통계
- false_negatives.md: 놓친 대어 분석

---

## 7. 데이터 무결성

### 7.1 백업
- GitHub: 유일한 기억 저장소
- 로컬 저장소: 작업 복사본

### 7.2 버전 관리
- 모든 루프 기록 유지
- 모든 복기 기록 유지
- 모든 성장룰 변경 이력 유지

### 7.3 감사 추적
- 모든 커밋에 타임스탬프 기록
- 모든 결정 근거 기록
- 모든 성과 측정 기록

---

## 8. 다음 루프 체크리스트

### 루프 시작 전
- [ ] GitHub 최신 상태 확인
- [ ] current_state.json 읽기
- [ ] growth_rules.md 읽기
- [ ] 최근 루프 결과 분석

### 루프 실행 중
- [ ] loop_data.json 생성
- [ ] loop_report.md 작성
- [ ] GitHub 커밋

### 루프 복기 중
- [ ] review_data.json 생성
- [ ] review_report.md 작성
- [ ] 새 성장룰 생성
- [ ] growth_rules.md 업데이트
- [ ] GitHub 커밋

### 루프 완료 후
- [ ] current_state.json 업데이트
- [ ] performance_log.json 업데이트
- [ ] GitHub 최종 커밋
