# HASOL 무료·무키 A–Z 운영 검증안
검증일: 2026-11-09 KST | 상태: **실험 코드 검증 / 운영 통합 일부 미완료 / CLEAN_FORWARD=0**

## 최종 결정
- **사용자가 할 일**: `루프시작` 또는 `루프복기시작` 입력만. 계정 생성·API 발급·결제·GitHub 설정 요청하지 않음.
- **실행 장소**: ChatGPT 대화에서 현재 연결된 Google Drive/Sheets 및 시장 데이터 도구 사용. GitHub는 무료 공개 소스의 반복 정량 테스트·실험 코드 저장용 보조 장치.
- **유일한 공식 정본**: `HASOL_EXTERNAL_BRAIN` Google Sheets. GitHub 리포지토리/실험 PR의 데이터는 정본이 아님.
- **아직 불가능한 보장**: 어떤 입력에서도 0오류, GitHub의 외부 인증 없는 24시간 무인 Brain 쓰기, 모든 미국 상장주식의 동일시점 PIT 정밀 데이터 확보, AI가 Simple보다 우수하다는 검증.
- **선택**: 새 프레임워크 도입보다 기존 `yfinance` + Nasdaq 공개 상장목록 + ChatGPT 연결된 Alpaca SIP + issuer primary source + Brain을 결합하는 **대화형 명령 실행**. 외부 독립 API 키 미요구.

## 실제 실행 검증 기록

**GitHub Actions 연결**: 실험 PR #32, 브랜치 `experiment/clean-a-b-c-20261109`에 자유 소스 프로브 `scripts/smoke_free_sources.py` 추가. 2026-11-09 UTC 07:15 표본 결과. GitHub Actions [RUN 42578089696](https://github.com/qkrgkfka0223-art/hasol-invest-os/actions/runs/42578089696) 성공, `python -m pytest -q tests` **103 passed**, 동일 커밋의 다른 3개 workflow도 성공.

| 검증 | 실제 결과 | 결론 |
|---|---|---|
| Nasdaq Trader `nasdaqlisted.txt` | HTTP 200, ETF·test 제외 4,318행 | 종목 초안 가능. 보통주 아님 |
| Nasdaq Trader `otherlisted.txt`, NYSE/NYSE American | HTTP 200, ETF·test 제외 3,111행 | 합계 **7,429**은 적격주 수가 아닌 목록 수 |
| 두 목록의 단순 제목·기호 1차 필터 | 3,208+2,384=**5,592** | 여전히 SPAC/ADR 등 구조적 검증 미완료 |
| yfinance 8종목 일봉 | **8/8**, 각 15개, 최근 2026-11-06 | 소규모 탐색 실동작 |
| yfinance 거래소 분산 표본 80종목 | **80/80** 조회, **79/80** 20거래일 보유 | 표본 수집 가능; 전체시장 확장 성공증거는 아님 |
| 동일 80종목의 정량적 가격/20D ADTV | 38/80 $3 이상 & 20D 평균달러 거래대금 $10M 이상 | **PROVISIONAL**; SPAC/ADR 등 적격성 별도 필요 |
| GitHub 실행환경 SEC submissions | **HTTP 403** | 서버의 직접 공식 공시 다운로드 실패; 필수 자동경로로 사용 금지 |
| GitHub 실행환경 SEC ticker exchange | **HTTP 403** | 동일. SEC 사이트 접근 자체 불가능하다고 일반화할 수 없음 |
| ChatGPT 연결 Alpaca SIP | 5종목 10거래일 SIP 일봉 성공 | 채팅 내 실가격 검증 가능. 외부 GitHub용 API 키를 뜻하지 않음 |
| ChatGPT 연결 Alpaca calendar | 2026-11-09~16 NYSE 일정 조회 성공 | 실제 평가 세션 계산 가능 |
| 기존 Brain 복원검사 | 23 RUN, Frozen 15건×20행, 11개 최종 복기, 4개 미래 평가 진행 중, Frozen 행 잠금 전수 일치 | **정본 읽기/상태 복원 가능**. 최신 live RUN 수행을 증명하는 것은 아님 |
| A/B/C + Blob 잠금·분석 | 103개 단위 테스트 완료 | 합성값 코드 검증. 실주식 예측력 검증 아님 |

Nasdaq 공식 목록 `File Creation Time: 1106202621:31`. 본 테스트는 **11/09 수집**했지만 파일 생성은 **11/06 21:31 ET**임을 별도로 기록. 데이터 신선도 없거나 시점 불일치하면 그대로 적시해야 함.

## A부터 Z까지 실행 계약

| 단계 | 실행 내용 | 실패 처리 |
|---|---|---|
| **A — Anchor** | 명령 시각 UTC/미국 ET, 이미 종료된 정규장 마지막 날짜·평가 시작 세션 확정 | 시각 또는 세션 미확정 → UNKNOWN |
| **B — Brain** | 공식 `00_CONTROL`, RUNS/FROZEN/OUTCOMES/REVIEWS/JOURNAL, 필요한 실험·규칙 재조회 | 과거 대화로 값 보충 금지 |
| **C — Checkpoint** | 중복 RUN ID, 기존 Frozen·Top5 정확성, 실패/미완료 후속작업 검사 | 상태 불일치 → DATA/PROCESS_FAIL 기록 |
| **D — Discovery seed** | Nasdaq·NYSE 거래소 명부 읽고 후보층 형성. ETF·test·부적격 기호 1차 필터 | 목록 접근 실패 → 이전 스냅샷은 구분하여 STALE 표기, 전체집합 주장 금지 |
| **E — Event** | 기업 IR 공시·실적·계약·가이던스 등 **가격 없는 발행사 1차자료** 확인 | SEC 403이면 IR/공식 발표로 교차검증, 수치 미확인 UNKNOWN |
| **F — Facts** | 공시 공개시각·출처·경영실적 변화·기대 대비 차이 기록 | 미래 공개 문서 사용 금지 |
| **G — Blind lock** | 가격·거래량·시장반응 접근 전에 기업정보와 price-blind 해석을 저장하고 SHA·readback 잠금 | 유출 발견 시 **영구 DEGRADED**, 그 RUN을 CLEAN으로 승격 금지 |
| **H — History** | 저비용 Yahoo 일봉으로 20D 가격/거래량/ATR/RVOL/상대강도 탐색 | 실패 종목은 UNKNOWN, Yahoo를 SIP 확정치로 오인 금지 |
| **I — Identity** | 보통주·직접 미국 상장 보통주, NYSE/NASDAQ/NYSE American, ADR/ETF/SPAC/우선주/워런트 제외 검증 | 종목명 추정으로 eligibility PASS 금지 |
| **J — Liquidity** | 가격≥$3, 상장≥20세션, 20일 ADTV≥$10M 적용 | 빠진 값은 UNKNOWN 및 미통과 |
| **K — Key source** | 연결된 시장 데이터 도구의 정규장 SIP·체결시각을 선정 20종목과 주요 challenger에 교차검증 | 데이터 연결 실패·무관측이면 확정가격을 창작하지 않음 |
| **L — Landscape** | 가격자료 이후 최근 수익률·갭·거래대금·시장 국면 판단 | 사후정보로 Blind 논거 역작성 금지 |
| **M — Mobility** | 향후 5세션 +10% **장중고가** 가능성/변동성/공급·희석/갭 소진 독립 비교 | 가능성과 기업 품질 분리 |
| **N — Numerics** | A: 가격·거래량 단순 규칙, B: 발행사 정보 변화 규칙을 별도 계산 | Structured 누락이면 UNSCORABLE, 임의 0점 대입 금지 |
| **O — Opinion** | C: HASOL AI 독립 순위. 최소 Top20보다 충분히 넓은 동시점 후보 평가 | 규칙 점수의 숨은 수동 보정 금지 |
| **P — Pairwise** | 상위 후보끼리 +10% 터치 상대가능성을 pairwise 비교 | 순위 변경 시 근거·반증 조건 기록 |
| **Q — Quality** | 세 방법의 동일 후보군/시점/기준가격 보장, 감점·미확인값 QA | 후보군이 다르면 A/B/C 우위 주장 금지 |
| **R — Record** | Official Top20/Top5·thesis/counter·baseline_price·observed_at·source·hash 준비 | 선택 20/5 불일치 또는 기준가 결측 → Official Frozen 불가, 시도 자체는 기록 |
| **S — Seal** | SHA-256 또는 확정 행 검증값으로 불변 Frozen 1회 기록 후 재조회 | 중복·덮어쓰기 금지, 실패 시 partial RUN 표시 |
| **T — Timetable** | NYSE 5개 세션 달력 고정. 장전 Frozen은 당일 S1; 장중 Frozen이면 **Frozen 전 일중 고가를 성공으로 세지 않음** | 분봉 없으면 장중 S1 정확 평가 UNKNOWN |
| **U — Update** | 평가 진행 중 S1~S4 고가와 목표 터치만 잠정기록, Final을 조기 선언하지 않음 | 미래 세션 값 보간 금지 |
| **V — Verify S5** | S5 종료 후 원본 Frozen price ×1.10 이상 달성 여부/첫 성공 세션/종가수익 확인 | 일봉·corporate action 불일치 검증 실패는 UNKNOWN |
| **W — Winners** | 공식 Top20/Top5 성공수, Discovery→Evaluated→Top20→Top5 승자 생존율, 실제 미국 전체 Eligible Top20/5 교집합 | 전체시장 freeze 시점 데이터 없으면 시장 Top20·recall UNKNOWN |
| **X — X-compare** | A/B/C에 **완전히 같은 전체 후보군**·같은 기준가격 사용, S5 결과로 비교 | 모델이 먼저 골라놓은 20개 안에서 재정렬한 것을 전체시장 기준선으로 속이지 않음 |
| **Y — Yield learning** | 첫 오류지점→가장 간단한 가설→반대가설→수정할 증거→반복 검증. 실험으로 관리 | 한 번 맞고 틀린 결과로 Production 규칙 변경 금지 |
| **Z — Zero user setup** | 명령 응답에 결과·검증상태·UNKNOWN·RUN ID·정본 링크 보고 | 인증 재설정 필요 시 사용자를 반복 호출하지 않고 현재 도구 범위 내 best effort |

## 실행 주체와 비용

| 영역 | 책임 주체 | 사용자 키/비용 |
|---|---|---|
| 공개 Nasdaq 명부 | GitHub 실험 수집기 / 대화 내 조회 | 무료·별도 키 없음 |
| Yahoo 가격 보조탐색 | 기존 `hasol_quant/yahoo_client.py` | 무료 접근 가능, 비공식/개인용·안정성 미보장 |
| SEC 공식 공시 | 대화 내 공식 문서 검색 + 회사 IR | 무료 원칙, GitHub 직접 403 실패 |
| 확정 가격·기존 SIP 가격 | 현재 **ChatGPT 연결된 Alpaca 데이터 도구** | 별도 외부 API 키 입력 없이 실조회 성공; 연결 의존 |
| 공식 Frozen·복기·복원 | HASOL_EXTERNAL_BRAIN (ChatGPT Google Drive 연결) | 추가 외부 인증 없음 |
| 24시간 무인 외부 쓰기 | GitHub Actions → Google Sheets API | **미완성**. 사용자 인증 불필요한 채팅 연결과 별개 |
| 자동매매/실거래 | **대상 아님** | 어떤 주문 권한도 필요하지 않음 |

**공개 소스 이용 제한**: yfinance는 Yahoo 비공식 개인 연구용 인터페이스이므로 사이트 약관에 유의하고 지속 과부하 요청/호출 회피를 하지 않음. SEC는 식별 가능한 User-Agent·공정 접근(현재 10req/s 한도) 준수. GitHub 저장소 현재 public이므로 비밀키·개인 식별정보·기밀 자료를 코드/로그/아티팩트에 올리지 않음.

## 장애·수정 기준

- **HTTP 403/429**: 증거 보존, 재시도 무한반복 금지, 다른 공식 IR 소스 확인. 막힌 데이터를 성공으로 취급하지 않음.
- **거래소 목록에 워런트/SPAC 존재**: ETF/Test 제외만으로 공통주식 적격 판정 금지.
- **SIP 제한/Quote stale**: source와 관측시각을 붙여서 검증. 잘못된 Frozen 기준가 추정 금지.
- **Price-Blind 오염**: source-only 탐색 직후 lock/readback 전까지 시장자료 노출 방지. 한 번 오염이면 되돌리지 않음.
- **장중 시점 누출**: 해당 날 정규장 전체 고가를 사전 Frozen 이후의 결과로 사용하지 않음.
- **결과 데이터의 전체 시장 미완성**: 실제 미국 전체 Eligible winner/recall은 UNKNOWN. 선택한 종목의 성공만 확정 평가.
- **시트/코드 불일치**: 정본의 LOCKED 기록 우선. GitHub 실험 브랜치는 정본 아님.
- **학습**: 복잡한 새 팩터 도입 금지; 기존 규칙 수정·통합·삭제 테스트 우선.

## 완료/미완료 판정

**확인 완료:** Nasdaq 2명부 무료 수집, Yahoo 8/8 및 80/80 표본 데이터, 79/80 20D, 정량 가격/거래대금 38/80 예비통과, ChatGPT Alpaca SIP·캘린더, Brain 원본 복원, 실험 A/B/C·불변성 합성 테스트 103개, CI 4개 성공.

**아직 미완료:** SEC GitHub direct 403, 전체 미 증권종류/SPAC PIT 확정, 무제한 무료 전체시장 ADTV(상장규모), ChatGPT price-blind upstream 분리, 자동 주가 수집 실패 시 동일 기준가격의 보장, A/B/C 실전 동시 Frozen+5세션 전방검증, 실제 미국시장 상승 Top20/5, CLEAN_FORWARD (정본 0), AI 우위 증명.

**운영 최종 판정:** `CHAT_COMMAND_BEST_EFFORT_READY` / `NO_EXTRA_USER_API_KEY` / `FULL_FREE_UNATTENDED_AUTOMATION_NOT_VERIFIED` / `CLEAN_FORWARD_UNPROVEN`.

**현실적 다음 단계:** 다음 실제 `루프시작`에서 전날 완료된 정규장 + 당일 발행사 공시를 Price-Blind 처리하고, 기존 무료후보+연결 Alpaca 검증을 사용해 A/B/C 전수 순위와 Official Frozen을 동일시점으로 저장한다. 이후 `루프복기시작`에서 5세션 평가와 독립 기준선 비교를 진행한다. 이 작업은 **사용자가 명령한 채팅 안에서 수행**하며, 해당 실제 RUN이 성공하기 전에는 '완전 구축'으로 표현하지 않는다.

### 근거 문서
- Nasdaq Trader listing directories: https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs
- Nasdaq live directory: https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt
- Yahoo yfinance disclaimers: https://ranaroussi.github.io/yfinance/
- SEC fair-access rules: https://www.sec.gov/about/developer-resources
- GitHub experiment PR: https://github.com/qkrgkfka0223-art/hasol-invest-os/pull/32
- Original canonical Brain: https://docs.google.com/spreadsheets/d/1hIThR4DcEQ2nmsVhNdEjTJOuKiHVQQkkGSsDjk2ZonY/edit
