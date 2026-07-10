# HASOL_ALPHA_V1.4 — Code/HASOL 역할 분리

## 목적

저런 급등주를 오른 뒤 보는 것이 아니라, 급등 전 후보풀에 넣기 위한 감지 엔진 기준을 고정한다.

```text
코드 = 감지 / 계산 / 기계적 분류 / CSV·JSON 생성
HASOL = 해석 / 시장판정 / 이벤트 질 판단 / Top20→Top5 압축 / 실행후보 분리 / 반대근거 / 다음 패치
```

## 코드가 해야 할 일

1. 후보풀을 넓게 만든다.
2. 가격·거래량·상대강도·시총·뉴스·공시·바이오 이벤트를 동일 기준으로 계산한다.
3. 종목의 현재 이동 단계를 `move_phase`로 분류한다.
4. Top20, Top5, execution_candidates, web_validation_checklist, run_metadata를 만든다.
5. 실행후보는 기본 잠금이다.

## HASOL이 직접 판단할 일

1. 시장이 GO / SOFT GO / NO TRADE인지 해석한다.
2. 오늘 돈이 갈 축을 정한다.
3. 코드가 잡은 이벤트가 실제 돈을 부를 이벤트인지 검증한다.
4. 가격이 초기인지, 추격인지, 클라이맥스인지 해석한다.
5. Top20을 웹검증하고 KEEP / WATCH / REJECT / MANUAL_REVIEW로 분류한다.
6. Top5와 execution_candidates를 분리한다.
7. 반대근거와 다음 코드 패치를 정한다.

## v1.4 핵심 변경

### 1. `move_phase` 추가

코드는 급등 전·중·후를 분리한다.

```text
EARLY_SIGNAL = +8~35% 구간, 거래량 확장, 과열 없음
GAP_EARLY_SIGNAL = 갭 초기, VWAP/전일고점 확인 필요
QUIET_RS_VOLUME_EXPANSION = 가격 급등 전 거래량 확장
HOT_SIGNAL_WATCH_ONLY = +35~80%, 관찰/눌림 필요
CLIMAX_REVIEW_ONLY = +80% 이상 또는 포물선/클라이맥스
POST_CLIMAX_FADE = 이전 급등 후 붕괴/반락
BASE_OR_QUIET_RS = 아직 초기 후보 또는 조용한 상대강도
```

### 2. 실행 가능 단계 분리

`execution_phase_ok`가 False면 Top5에는 들어갈 수 있어도 실행후보는 아니다.

실행 가능 후보는 원칙적으로 다음 단계만 허용한다.

```text
EARLY_SIGNAL
GAP_EARLY_SIGNAL
QUIET_RS_VOLUME_EXPANSION
BASE_OR_QUIET_RS
```

### 3. 과열 잠금 강화

다음은 실행후보가 아니라 복기/관찰이다.

```text
HOT_SIGNAL_WATCH_ONLY
CLIMAX_REVIEW_ONLY
POST_CLIMAX_FADE
```

## 공식 출력 해석

```text
Top20 = 웹검증 대상
Top5 = 강한 예측 후보
execution_candidates = 실행 검토 후보
```

Top5와 execution_candidates는 같지 않다.

## HASOL 최종 출력 순서

```text
1. 공식 루프 실행 여부
2. 시장판정
3. 후보 수
4. Top20
5. 웹검증 통과
6. Top5
7. 실행후보
8. 최종결론
9. 반대근거
10. 다음 패치
```

## 금지

```text
코드 결과 없이 live run이라고 말하기 금지
Top5를 실행후보처럼 말하기 금지
CLIMAX 종목을 매수후보처럼 말하기 금지
웹검증 전 execution 확정 금지
하람 승인 전 실행 확정 금지
```
