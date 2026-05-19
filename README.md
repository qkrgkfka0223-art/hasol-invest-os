# HASOL_INVEST_OS

**자율 진화형 미국주식 상승확률 Top20 압축 엔진**

웹 기반 후보 발굴 → 가격 검증 → GitHub 기억 → 복기를 통한 성장

---

## 핵심 목표

감지 시점 기준으로 이후 상승확률이 높은 미국주식 Top20 압축

---

## 외부뇌 (External Brain)

**GitHub = 유일한 기억 저장소**

- ✅ Google Sheet 의존 제거
- ✅ 모든 루프 기록 누적
- ✅ 모든 성장룰 누적
- ✅ 모든 성과 추적

자세한 구조: [`EXTERNAL_BRAIN_STRUCTURE.md`](./EXTERNAL_BRAIN_STRUCTURE.md)

---

## 디렉토리 구조

```
hasol-invest-os/
├── README.md                        # 프로젝트 개요
├── EXTERNAL_BRAIN_STRUCTURE.md      # 외부뇌 구조
├── docs/
│   └── HASOL_PROTOCOL.md            # 운영 헌법
├── state/
│   ├── current_state.json           # 현재 루프 상태
│   └── loop_history.json            # 모든 루프 히스토리
├── rules/
│   ├── growth_rules.md              # 성장룰 (누적)
│   └── filters/
│       ├── hard_filters.json        # Hard Filter 규칙
│       ├── soft_filters.json        # Soft Filter 규칙
│       └── scoring_rules.json       # 점수 계산 규칙
├── runs/
│   ├── loop_20260518/
│   │   ├── loop_20260518_final_report.md
│   │   └── loop_20260518_final_result.json
│   └── loop_20260517/
│       ├── loop_20260517_final_report.md
│       └── loop_20260517_final_result.json
├── logs/
│   └── error_log.json               # 에러 로그
└── analysis/
    ├── top20_analysis.json          # Top20 분석
    ├── top3_analysis.json           # Top3 분석
    └── success_rate.json            # 성공률 통계
```

---

## 루프 순서

```
루프준비 → 루프시작 → 가격검증 → 정밀검증 → 루프종료 기록 → 복기 → 성장반영
```

### 1. 루프준비 (Loop Preparation)
- GitHub 읽기
- 성장룰 반영
- 현재 상태 확인

### 2. 루프시작 (Loop Start)
- 웹 기반 후보 발굴
- Top20 압축
- 가격 검증
- Top3 선정
- 시장판정
- 루프 기록

### 3. 루프복기 (Loop Review) - 선택
- 성과 측정
- 실패 원인 분석
- 성장룰 생성

### 4. 성장반영 (Growth Reflection)
- 새 성장룰 적용
- 다음 루프 준비

---

## 트리거 신호

| 신호 | 동작 |
|------|------|
| `루프시작` | 웹에서 오늘 후보 발굴 |
| `루프복기` | 감지 판단 검증 |
| `기록해` | 확정 결과 저장 |

---

## 최신 루프 상태

**Loop ID**: `LOOP_20260518`  
**Status**: 루프종료 기록 완료  
**Market Signal**: GO  
**Top20**: 20개 확정  
**Execution Candidates**: 5개 확정

### Top3 (상승확률 순)
1. **NVDA** (95%) - 반도체 강세 + 실적 깜짝
2. **RAMP** (92%) - AI 인프라 + Publicis 계약
3. **MU** (90%) - 반도체 강세 + AI 칩 수요

---

## 성장 메커니즘

### 성공 기준
- **루프 성공**: Top3 중 1개 이상 10% 이상 상승
- **예측률 목표**: 70% 이상

### 성장 단계
- **Loop 1-10**: 80% 이상 목표
- **Loop 11-30**: 85% 이상 목표
- **Loop 31+**: 90% 이상 목표

### 성장룰 누적
- 매 루프마다 새로운 성장룰 생성
- 반복 실패 패턴 제거
- 성공률 향상

---

## 커밋 규칙

```
[LOOP_YYYYMMDD_NN] 루프 실행 완료 - Top20: XX, Top3: XX, Market: GO/SOFT_GO/NO_TRADE
[REVIEW_YYYYMMDD_NN] 루프 복기 완료 - 성공률: XX%
[GROWTH_RULES] 성장룰 업데이트 - Rule YYYYMMDD-XX 추가
[CLEANUP] 불필요한 파일 정리
```

---

## 다음 루프 체크리스트

### 루프 시작 전
- [ ] GitHub 최신 상태 확인
- [ ] `current_state.json` 읽기
- [ ] `growth_rules.md` 읽기
- [ ] 최근 루프 결과 분석

### 루프 실행 중
- [ ] 웹 기반 후보 발굴
- [ ] Top20 압축
- [ ] 가격 검증
- [ ] Top3 선정
- [ ] 시장판정
- [ ] 루프 기록 및 커밋

### 루프 복기 중 (선택)
- [ ] 성과 측정
- [ ] 실패 원인 분석
- [ ] 성장룰 생성
- [ ] 복기 기록 및 커밋

---

## 성과 기록

| 루프 | 날짜 | 시장판정 | Top3 | 성공률 | 비고 |
|------|------|---------|------|--------|------|
| LOOP_20260518 | 2026-05-18 | GO | NVDA, RAMP, MU | - | 실행 대기 |
| LOOP_20260517 | 2026-05-17 | GO | - | - | 기록 완료 |

---

## 참고 문서

- [`EXTERNAL_BRAIN_STRUCTURE.md`](./EXTERNAL_BRAIN_STRUCTURE.md) - 외부뇌 구조 상세
- [`docs/HASOL_PROTOCOL.md`](./docs/HASOL_PROTOCOL.md) - 운영 헌법
- [`rules/growth_rules.md`](./rules/growth_rules.md) - 성장룰 (누적)

---

**마지막 업데이트**: 2026-05-19 UTC
