# HASOL_INVEST_OS

**자율 진화형 미국주식 상승확률 Top20 압축 엔진**

웹 기반 후보 발굴 → 가격 검증 → GitHub 기억 → 복기를 통한 성장

## 핵심 목표

감지 시점 기준으로 이후 상승확률이 높은 미국주식 Top20 압축

## 구조

```
docs/          → HASOL_PROTOCOL.md (운영 헌법)
state/         → current_state.json (현재 상태)
rules/         → growth_rules.md (성장룰)
logs/          → error_log.json (에러 로그)
runs/          → 루프별 실행 기록
  ├── audit_*.md
  ├── loop_*.md
  └── loop_YYYYMMDD/
      ├── loop_YYYYMMDD_final_report.md
      └── loop_YYYYMMDD_final_result.json
```

## 루프 순서

1. **루프준비** → GitHub 읽기
2. **루프시작** → 웹 기반 후보 발굴
3. **가격검증** → 실행 후보 확정 전 필수
4. **정밀검증** → 반대근거 검토
5. **루프종료 기록** → GitHub 저장
6. **루프복기** (선택) → 감지 판단 검증
7. **성장반영** (선택) → 성장룰 생성

## 트리거 신호

- `루프시작` → 웹에서 오늘 후보 발굴
- `루프복기` → 감지 판단 검증
- `기록해` → 확정 결과 저장

## 최신 루프

- **Loop ID**: LOOP_20260517_COMPLETE
- **Top20**: 13개 확정
- **실행 후보**: 10개 확정
- **시장 신호**: SOFT_GO

## 성장 기준

- 예측률 70% 이상 달성
- 반복 실패 패턴 제거
- 성장룰 누적 적용
