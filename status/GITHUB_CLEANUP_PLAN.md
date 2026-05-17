# GitHub 정리 계획

## 【현재 상태】

### 루트 폴더 (지저분함)
```
./STATUS.md
./GITHUB_STRUCTURE_PLAN.md
./README.md
./PROTOCOL_REVIEW_20260517.md
./HASOL_COMPLETE_STRATEGY.md
./LOOP_READINESS_CHECK.md
./ANALYSIS_MY_MISTAKES.md
./GROWTH_REANALYSIS_20260517.md
./LOOP_CRITERIA_ANALYSIS_20260517.md
./MY_FUNDAMENTAL_PROBLEMS.md
./HASOL_PROTOCOL.md
```

**문제**: 11개 파일이 루트에 흩어져 있음

### 폴더 구조 (부분적)
```
state/
  - current_state.json
rules/
  - growth_rules.md
logs/
  - error_log.json
runs/
  - loop_20260517_*.md (여러 파일)
  - *.json (여러 파일)
```

**문제**: 루트 파일들이 정리되지 않음

---

## 【정리 계획】

### Step 1: 루트 파일 분류

**프로토콜/전략 (docs/ 폴더로 이동)**
- HASOL_PROTOCOL.md → docs/HASOL_PROTOCOL.md
- HASOL_COMPLETE_STRATEGY.md → docs/HASOL_COMPLETE_STRATEGY.md
- GITHUB_STRUCTURE_PLAN.md → docs/GITHUB_STRUCTURE_PLAN.md

**성장/학습 (learning/ 폴더로 이동)**
- ANALYSIS_MY_MISTAKES.md → learning/ANALYSIS_MY_MISTAKES.md
- GROWTH_REANALYSIS_20260517.md → learning/GROWTH_REANALYSIS_20260517.md
- LOOP_CRITERIA_ANALYSIS_20260517.md → learning/LOOP_CRITERIA_ANALYSIS_20260517.md
- MY_FUNDAMENTAL_PROBLEMS.md → learning/MY_FUNDAMENTAL_PROBLEMS.md
- PROTOCOL_REVIEW_20260517.md → learning/PROTOCOL_REVIEW_20260517.md

**상태/체크리스트 (status/ 폴더로 이동)**
- STATUS.md → status/STATUS.md
- LOOP_READINESS_CHECK.md → status/LOOP_READINESS_CHECK.md
- GITHUB_CLEANUP_PLAN.md → status/GITHUB_CLEANUP_PLAN.md

**루트 유지**
- README.md (프로젝트 개요)
- .gitignore (git 설정)

### Step 2: runs 폴더 정리

**현재:**
```
runs/
  - loop_20260517_market_signal.md
  - loop_20260517_price_validation.md
  - loop_20260517_final_report.md
  - loop_20260517_rejudgment.md
  - loop_20260517_final_result.json
  - investing_com_stocks.json
  - top_30_momentum.json
  - top30_analysis.json
  - final_top20_candidates.json
  - final_top20_with_validation.json
```

**정리:**
```
runs/
  loop_20260517/
    - market_signal.md
    - price_validation.md
    - rejudgment.md
    - final_report.md
    - final_result.json
    - data/
      - investing_com_stocks.json
      - top_30_momentum.json
      - top30_analysis.json
      - final_top20_candidates.json
      - final_top20_with_validation.json
```

### Step 3: 폴더 구조 최종

```
hasol-invest-os/
├── README.md                          (프로젝트 개요)
├── .gitignore
│
├── docs/                              (프로토콜/전략)
│   ├── HASOL_PROTOCOL.md
│   ├── HASOL_COMPLETE_STRATEGY.md
│   └── GITHUB_STRUCTURE_PLAN.md
│
├── learning/                          (성장/학습)
│   ├── ANALYSIS_MY_MISTAKES.md
│   ├── GROWTH_REANALYSIS_20260517.md
│   ├── LOOP_CRITERIA_ANALYSIS_20260517.md
│   ├── MY_FUNDAMENTAL_PROBLEMS.md
│   └── PROTOCOL_REVIEW_20260517.md
│
├── status/                            (상태/체크리스트)
│   ├── STATUS.md
│   ├── LOOP_READINESS_CHECK.md
│   └── GITHUB_CLEANUP_PLAN.md
│
├── state/                             (현재 상태)
│   └── current_state.json
│
├── rules/                             (성장 룰)
│   └── growth_rules.md
│
├── logs/                              (오류 로그)
│   └── error_log.json
│
└── runs/                              (루프 기록)
    └── loop_20260517/
        ├── market_signal.md
        ├── price_validation.md
        ├── rejudgment.md
        ├── final_report.md
        ├── final_result.json
        └── data/
            ├── investing_com_stocks.json
            ├── top_30_momentum.json
            ├── top30_analysis.json
            ├── final_top20_candidates.json
            └── final_top20_with_validation.json
```

---

## 【정리 규칙】

### 파일 분류 기준

**docs/** - 운영 문서
- 프로토콜, 전략, 구조 설계
- 변경 빈도: 낮음
- 용도: 참고용

**learning/** - 성장 기록
- 실수 분석, 재판단, 문제 분석
- 변경 빈도: 높음 (루프마다 추가)
- 용도: 복기 및 성장

**status/** - 상태 관리
- 현재 상태, 체크리스트, 정리 계획
- 변경 빈도: 중간
- 용도: 진행 상황 추적

**state/** - 현재 상태 (JSON)
- current_state.json만
- 변경 빈도: 높음 (루프마다)
- 용도: 루프 준비 시 로드

**rules/** - 성장 룰
- growth_rules.md만
- 변경 빈도: 중간 (복기 후 추가)
- 용도: 다음 루프 적용

**logs/** - 오류 로그
- error_log.json만
- 변경 빈도: 낮음
- 용도: 오류 추적

**runs/** - 루프 기록
- 루프별 폴더 (loop_YYYYMMDD/)
- 변경 빈도: 높음 (루프마다)
- 용도: 루프 기록 및 복기

---

## 【Git 커밋 규칙】

### 커밋 메시지 형식

**루프 기록:**
```
feat: Loop YYYYMMDD - [간단한 설명]
예: feat: Loop 20260517 - Top 20 confirmed, 8 execution candidates
```

**성장 기록:**
```
docs: Learning - [간단한 설명]
예: docs: Learning - Growth reanalysis with clear judgment criteria
```

**상태 업데이트:**
```
update: Status - [간단한 설명]
예: update: Status - GitHub cleanup and reorganization
```

**파일 정리:**
```
chore: Cleanup - [간단한 설명]
예: chore: Cleanup - Reorganize root files into folders
```

---

## 【실행 순서】

1. docs/ 폴더 생성 및 파일 이동
2. learning/ 폴더 생성 및 파일 이동
3. status/ 폴더 생성 및 파일 이동
4. runs/loop_20260517/ 폴더 생성 및 파일 정리
5. runs/loop_20260517/data/ 폴더 생성 및 JSON 파일 이동
6. Git 커밋

---

**이제 GitHub를 제대로 관리합니다.**
