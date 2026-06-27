# HASOL_DETECTOR_V1.2 RUN REPORT

## 실행 결과

- mode: sample
- market_code: SOFT_GO
- raw_count: 30
- top20_count: 19
- top5_count: 5
- execution_policy: LOCKED_UNTIL_WEB_VALIDATION

## Top5

1. CRVO / micro_cap / INSIDER_BUY / score 66.41
2. RXT / small_cap / AI_INFRA;DATA_CENTER / score 62.82
3. LUNR / mid_cap / SPACE;GOV_CONTRACT / score 62.32
4. IESC / large_cap / EARNINGS / score 61.11
5. AMD / mega_cap / AI_INFRA;DATA_CENTER / score 55.61

## 결론

v1.2는 샘플/라이브 모드를 분리했고, sample 결과는 `SAMPLE_ONLY_DO_NOT_TRADE`로 잠근다.
라이브 모드에서도 웹 정밀검증 전에는 매수 판단이 아니다.

## 다음 단계

1. 로컬/서버에서 yfinance 설치 후 live mode 실행
2. top20_candidates.csv를 웹 검증
3. KEEP/WATCH/REJECT/EXECUTION_CANDIDATE 분리
4. 검증 통과 건만 01_PREDICTION 기록
