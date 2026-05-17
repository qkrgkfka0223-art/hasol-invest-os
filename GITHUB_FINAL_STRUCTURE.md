# GitHub 최종 파일 구조 (누적 구조)

## 【핵심 원칙】

1. **파일은 최소한으로** - 필요한 것만
2. **누적 구조** - 루프마다 추가, 덮어쓰기 없음
3. **JSON 기반** - 구조화된 데이터
4. **버전 관리** - Git으로 모든 변경 추적

---

## 【최종 파일 목록】

### 1. docs/HASOL_PROTOCOL.md (고정)
- **용도**: 운영 헌법
- **변경**: 거의 없음 (프로토콜 변경 시만)
- **내용**: 7단계 루프, 트리거 동작, 금지 원칙

### 2. state/current_state.json (매 루프 업데이트)
- **용도**: 현재 상태
- **구조**:
```json
{
  "current_loop": "LOOP_20260517",
  "status": "LOOP_COMPLETE",
  "last_update": "2026-05-17T12:00:00Z",
  "market_signal": "SOFT_GO",
  "top20_count": 8,
  "execution_candidates": 8
}
```

### 3. rules/growth_rules.md (누적)
- **용도**: 성장 룰
- **구조**: 마크다운 리스트
- **추가**: 복기 후 새 룰 추가 (덮어쓰기 없음)
- **예시**:
```markdown
## 성장 룰

### Loop 20260517
- Rule 1: 촉매 불명확 제외
- Rule 2: 테마 중복 제외
- Rule 3: 72시간 촉매 제외

### Loop 20260516
- Rule 1: ...
```

### 4. logs/error_log.json (누적)
- **용도**: 오류 로그
- **구조**: JSON 배열
- **추가**: 오류 발생 시 추가 (덮어쓰기 없음)
- **예시**:
```json
[
  {
    "loop_id": "LOOP_20260517",
    "error": "판단 회피",
    "cause": "기계적 필터만 적용",
    "solution": "각 종목마다 왜? 기록"
  }
]
```

### 5. runs/loop_YYYYMMDD/final_report.md (누적)
- **용도**: 최종 보고서
- **구조**: 마크다운
- **내용**:
  - Top20 리스트
  - 실행 후보
  - 시장 판정
  - 판단 기준
  - 성장 룰 적용

### 6. runs/loop_YYYYMMDD/final_result.json (누적)
- **용도**: 최종 결과 (구조화)
- **구조**: JSON
- **내용**:
```json
{
  "loop_id": "LOOP_20260517",
  "timestamp": "2026-05-17T12:00:00Z",
  "market_status": "SOFT_GO",
  "top20": [
    {
      "rank": 1,
      "ticker": "ENPH",
      "name": "인페이즈 에너지",
      "catalyst": "상업용 제품 확대",
      "judgment": "진입 가능",
      "confidence": "높음"
    }
  ],
  "execution_candidates": 8
}
```

### 7. reviews/review_log.json (누적)
- **용도**: 복기 기록
- **구조**: JSON 배열
- **추가**: 복기 후 추가 (덮어쓰기 없음)
- **예시**:
```json
[
  {
    "review_date": "2026-05-18",
    "loop_id": "LOOP_20260517",
    "days_after": 1,
    "max_gain": 5.2,
    "max_loss": -2.1,
    "success_count": 6,
    "failure_count": 2,
    "growth_rules_generated": 3
  }
]
```

---

## 【파일 구조 다이어그램】

```
hasol-invest-os/
├── docs/
│   └── HASOL_PROTOCOL.md              # 고정 (운영 헌법)
│
├── state/
│   └── current_state.json             # 매 루프 업데이트
│
├── rules/
│   └── growth_rules.md                # 누적 (복기 후 추가)
│
├── logs/
│   └── error_log.json                 # 누적 (오류 발생 시 추가)
│
├── runs/
│   ├── loop_20260517/
│   │   ├── final_report.md            # 누적 (루프마다 추가)
│   │   └── final_result.json          # 누적 (루프마다 추가)
│   ├── loop_20260516/
│   │   ├── final_report.md
│   │   └── final_result.json
│   └── ...
│
└── reviews/
    └── review_log.json                # 누적 (복기 후 추가)
```

---

## 【루프 흐름에 따른 파일 변경】

### 루프시작 → 루프종료
1. **state/current_state.json** 업데이트
   - current_loop: LOOP_YYYYMMDD
   - status: LOOP_COMPLETE
   - top20_count: N
   - execution_candidates: N

2. **runs/loop_YYYYMMDD/final_report.md** 생성
   - Top20 리스트
   - 판단 기준
   - 성장 룰 적용

3. **runs/loop_YYYYMMDD/final_result.json** 생성
   - 구조화된 결과

### 복기시작 → 복기종료
1. **reviews/review_log.json** 추가
   - 복기 결과
   - 성과 분석
   - 실패 원인

2. **rules/growth_rules.md** 추가
   - 새 성장 룰

3. **logs/error_log.json** 추가 (필요 시)
   - 오류 기록

---

## 【삭제할 파일】

### 즉시 삭제
```
rm -rf learning/
rm -rf status/
rm README.md
rm docs/HASOL_COMPLETE_STRATEGY.md
rm docs/GITHUB_STRUCTURE_PLAN.md
rm runs/loop_20260517/market_signal.md
rm runs/loop_20260517/price_validation.md
rm runs/loop_20260517/rejudgment.md
rm -rf runs/loop_20260517/data/
```

---

## 【파일 관리 규칙】

### 고정 파일 (거의 변경 없음)
- docs/HASOL_PROTOCOL.md
- 변경 시: Git 커밋 기록

### 업데이트 파일 (매 루프 변경)
- state/current_state.json
- 변경 시: Git 커밋 기록

### 누적 파일 (루프/복기마다 추가)
- rules/growth_rules.md
- logs/error_log.json
- runs/loop_YYYYMMDD/final_report.md
- runs/loop_YYYYMMDD/final_result.json
- reviews/review_log.json
- 변경 시: Git 커밋 기록 (추가만, 덮어쓰기 없음)

---

## 【Git 커밋 규칙】

### 루프 완료
```
feat: Loop YYYYMMDD - Top20 confirmed, N execution candidates
```

### 상태 업데이트
```
update: State - Loop YYYYMMDD complete
```

### 복기 완료
```
docs: Review - Loop YYYYMMDD, N days after, M growth rules
```

### 오류 기록
```
docs: Error log - ERROR_NNN: [설명]
```

---

## 【성장 요소 (파일에 기록되는 것)】

### 1. 판단 기준 (final_report.md에 기록)
- 웹 신호 분석
- 촉매 파악
- 리스크 평가
- 최종 판단

### 2. 성장 룰 (growth_rules.md에 누적)
- 반복 실패 방지 규칙
- 기계적으로 적용 가능
- 다음 루프에 적용

### 3. 복기 결과 (review_log.json에 누적)
- 감지 판단 검증
- 성과 분석
- 실패 원인

### 4. 오류 개선 (error_log.json에 누적)
- 오류 인식
- 원인 분석
- 해결 방법

---

**이제 파일 구조가 명확합니다.**
