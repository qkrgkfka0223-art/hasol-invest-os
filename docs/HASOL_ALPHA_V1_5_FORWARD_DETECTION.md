# HASOL_ALPHA_V1.5 — Forward Detection Loop

## 한 줄 정의

```text
GitHub 코드로 넓게 받고, 웹검증으로 좁게 확인해서, 감지시점 이후 오를 확률 높은 미국주식을 찾는다.
```

## 목적

이미 오른 종목을 찾는 것이 아니다.

```text
오른 종목 = 복기 재료
오를 확률 높은 종목 = 메인 루프 대상
```

## 루프 정의

```text
1. GitHub Actions 실행
2. 넓은 후보 파일 생성
3. HASOL이 Top20을 읽음
4. 웹검색으로 뉴스/SEC/FDA/실적/현재가/거래량 정밀검증
5. KEEP / WATCH / REJECT / MANUAL_REVIEW 분류
6. validated Top5 압축
7. execution_candidates 분리
8. 결과 기록과 다음 코드 패치 결정
```

## 코드가 넓게 받아야 할 후보

### 1. 미래 이벤트 후보

```text
earnings upcoming
PDUFA upcoming
FDA advisory committee
clinical readout expected
investor day
product launch
government contract cycle
policy catalyst
```

### 2. 신선한 촉매 + 덜 오른 가격

```text
8-K material agreement
Form 4 code P insider buy
13D / 13G ownership change
earnings beat / guidance raise
FDA approval / BLA / NDA / clinical success
major contract / strategic partnership
```

가격 조건:

```text
0~20% = 우선검토
20~35% = 조심
35~80% = WATCH 우선
80% 이상 = 복기/관찰
```

### 3. 조용한 상대강도

```text
20일선 위
50일선 위
SPY/QQQ 대비 강함
거래량 초기 증가
전고점 근처에서 안 죽음
뉴스는 아직 크지 않음
```

## HASOL 판단 기준

```text
왜 앞으로 돈이 들어오나?
왜 아직 늦지 않았나?
왜 시장이 아직 덜 반영했나?
이 이벤트는 진짜인가?
가격계획과 무효선이 있는가?
뭐가 이 판단을 틀리게 만드나?
```

## 출력 금지

```text
후보와 실행후보 섞기 금지
Top5를 매수후보처럼 말하기 금지
오른 종목을 메인 후보처럼 말하기 금지
웹검증 전 실행후보 확정 금지
```

## 공식 출력

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
