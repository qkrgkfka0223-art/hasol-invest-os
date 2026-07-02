# Backtest Rule

현재 v1.4는 후보수집기다.

다음 단계는 과거 일별 급등 종목 기준으로 다음을 검증한다.

```text
1. 실제 오른 종목이 raw_candidates에 있었는가
2. raw에는 있었는데 filter에서 죽었는가
3. scored에는 있었는데 Top20에서 빠졌는가
4. Top20에는 있었는데 Top5에서 빠졌는가
5. execution_candidates까지 갔는가
```

분류:

```text
DETECTION_FAIL = 후보풀에도 없음
FILTER_FAIL = 후보풀에는 있었으나 제거됨
COMPRESSION_FAIL = 점수화 후 Top20/Top5 압축 실패
EXECUTION_FAIL = 후보는 맞았으나 실행조건 실패
```

이 검증 없이 100점 코드라고 말하지 않는다.
