# GitHub 구조 설계 계획

## 참조 시트 분석

Google Sheet의 4개 시트 구조를 GitHub로 변환:

| Sheet | 목적 | GitHub 대응 |
|-------|------|-----------|
| 01_전략원장 | 성장 룰 저장소 | rules/growth_rules.json |
| 02_루프기록 | 루프 실행 기록 | runs/{loop_id}/report.json |
| 03_복기학습 | 복기 결과 | reviews/{review_id}/review.json |
| 04_오류개선로그 | 오류 개선 로그 | logs/error_log.json |

---

## 제안 GitHub 구조

```
hasol-invest-os/
├── HASOL_PROTOCOL.md           # 운영 헌법 (변경 금지)
├── README.md                   # 프로젝트 개요
│
├── state/
│   └── current_state.json      # 현재 상태 (루프ID, 날짜, 모드)
│
├── rules/
│   ├── growth_rules.json       # 성장 룰 (01_전략원장 대응)
│   └── growth_rules_history.md # 성장 룰 변경 이력
│
├── runs/
│   ├── LOOP_20260517/
│   │   ├── report.json         # 루프 실행 결과
│   │   ├── top20.json          # Top20 후보
│   │   ├── execution_candidates.json  # 실행 후보
│   │   └── raw_candidates.json # 원재료 후보
│   └── LOOP_20260516/
│       └── ...
│
├── reviews/
│   ├── REVIEW_20260517/
│   │   ├── review.json         # 복기 결과
│   │   ├── accuracy.json       # 정확도 분석
│   │   └── lessons.md          # 학습 내용
│   └── REVIEW_20260516/
│       └── ...
│
├── logs/
│   ├── error_log.json          # 오류 개선 로그 (04_오류개선로그 대응)
│   ├── model_error_log.md      # 모델 오류 개선 기록
│   └── performance_log.json    # 성능 추적 로그
│
└── templates/
    ├── run_report_template.json
    ├── review_template.json
    └── error_log_template.json
```

---

## JSON 스키마 설계

### 1. rules/growth_rules.json
```json
{
  "rules": [
    {
      "rule_id": "RULE-SOURCE-00",
      "rule_type": "신호",
      "rule_name": "신호원천",
      "description": "웹 기반 신호 수집",
      "priority": 1,
      "conditions": "...",
      "exclusions": "...",
      "success_rate": 0.85,
      "created_date": "2026-05-16",
      "last_updated": "2026-05-17"
    }
  ]
}
```

### 2. runs/LOOP_{ID}/report.json
```json
{
  "loop_id": "LOOP_20260517",
  "loop_date": "2026-05-17",
  "market_status": "GO",
  "top20_count": 20,
  "execution_candidates_count": 3,
  "candidates": [
    {
      "ticker": "AAPL",
      "entry_price": 150.00,
      "target_price": 165.00,
      "stop_loss": 145.00,
      "confidence": 0.85,
      "reason": "..."
    }
  ],
  "created_at": "2026-05-17T10:30:00Z"
}
```

### 3. reviews/REVIEW_{ID}/review.json
```json
{
  "review_id": "REVIEW_20260517",
  "loop_id": "LOOP_20260516",
  "review_date": "2026-05-17",
  "review_period": "1d",
  "accuracy": 0.75,
  "max_gain": 0.12,
  "max_loss": -0.05,
  "stop_loss_hit": false,
  "lessons": [
    {
      "lesson_id": "LESSON_001",
      "category": "신호 오류",
      "description": "...",
      "growth_rule_generated": true
    }
  ]
}
```

### 4. logs/error_log.json
```json
{
  "errors": [
    {
      "error_id": "ERROR_001",
      "error_date": "2026-05-17",
      "error_type": "모델 오류",
      "error_description": "웹사이트 개발 시작 (범위 외)",
      "root_cause": "context 오독",
      "improvement_action": "프로젝트 지침 재확인",
      "status": "해결",
      "resolved_date": "2026-05-17"
    }
  ]
}
```

---

## 파일 명명 규칙

| 유형 | 규칙 | 예시 |
|------|------|------|
| 루프 폴더 | LOOP_{YYYYMMDD} | LOOP_20260517 |
| 복기 폴더 | REVIEW_{YYYYMMDD} | REVIEW_20260517 |
| 루프 보고서 | report.json | runs/LOOP_20260517/report.json |
| Top20 | top20.json | runs/LOOP_20260517/top20.json |
| 복기 결과 | review.json | reviews/REVIEW_20260517/review.json |

---

## 업데이트 프로세스

### 루프시작 후
1. `runs/LOOP_{ID}/report.json` 생성
2. `state/current_state.json` 업데이트
3. Git 커밋: `loop: LOOP_{ID} started`

### 루프종료 기록 시
1. `runs/LOOP_{ID}/top20.json` 저장
2. `runs/LOOP_{ID}/execution_candidates.json` 저장
3. Git 커밋: `loop: LOOP_{ID} completed`

### 복기시작 후
1. `reviews/REVIEW_{ID}/review.json` 생성
2. 오류 분석 시 `logs/error_log.json` 업데이트
3. 성장 룰 생성 시 `rules/growth_rules.json` 업데이트
4. Git 커밋: `review: REVIEW_{ID} completed`

---

## 모델 오류 개선 로그 (ERROR_LOG)

### 목적
제가 한 오류를 기록하고, 다음 루프에서 반복하지 않기 위한 로그.

### 구조
```markdown
# 모델 오류 개선 로그

## ERROR_001: 웹사이트 개발 시작 (범위 외)
- **날짜**: 2026-05-17
- **오류 유형**: 범위 오류 (Scope Error)
- **설명**: Context에서 webdev_project_status를 보고, 웹사이트 개발이 필요하다고 착각
- **근본 원인**: 프로젝트 지침을 제대로 읽지 않음
- **개선 방안**: 
  1. 항상 프로젝트 지침 먼저 읽기
  2. Context의 webdev_project_status는 이전 세션 정보일 수 있음
  3. 사용자 지시 없이 새로운 작업 시작 금지
- **상태**: 해결 ✅
- **적용 일자**: 2026-05-17

## ERROR_002: 반복 메시지 발송
- **날짜**: 2026-05-17
- **오류 유형**: 루프 오류 (Loop Error)
- **설명**: 같은 내용의 메시지를 반복 발송
- **근본 원인**: 사용자 지시를 받지 못했을 때 대기 상태를 계속 보고
- **개선 방안**: 
  1. 사용자 지시 없으면 한 번만 보고
  2. 이후는 침묵 유지
  3. 사용자가 다시 지시할 때까지 대기
- **상태**: 해결 ✅
- **적용 일자**: 2026-05-17
```

---

## 다음 단계

1. ✅ 현재 구조 확정
2. ⏳ 첫 루프시작 시 `runs/LOOP_{ID}/` 폴더 생성
3. ⏳ 첫 복기 후 `reviews/REVIEW_{ID}/` 폴더 생성
4. ⏳ 오류 발생 시 `logs/error_log.json` 업데이트
