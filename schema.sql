CREATE TABLE loops (
        loop_id TEXT PRIMARY KEY,
        date TEXT,
        market_status TEXT,
        main_axis TEXT,
        block_axis TEXT
    );
CREATE TABLE stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loop_id TEXT,
        ticker TEXT,
        discovery_path TEXT,
        current_price REAL,
        entry_price REAL,
        target_price REAL,
        stop_loss REAL,
        r_value REAL,
        bear_scenarios TEXT,
        decision TEXT, -- TOP3, TOP20, WATCH, EXCLUDE
        FOREIGN KEY (loop_id) REFERENCES loops (loop_id)
    );
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loop_id TEXT,
        ticker TEXT,
        review_day INTEGER, -- 3, 7, 10, 14
        price_at_review REAL,
        performance REAL,
        status TEXT, -- SUCCESS, PARTIAL, FAIL
        root_cause TEXT,
        FOREIGN KEY (loop_id) REFERENCES loops (loop_id)
    );
CREATE TABLE market_sensing (
    sensing_date TEXT PRIMARY KEY,
    market_status TEXT NOT NULL, -- GO, SOFT_GO, NO_TRADE
    sp500_price REAL,
    nasdaq_price REAL,
    vix_index REAL,
    yield_10y REAL,
    leading_sectors TEXT, -- 주도 섹터 (JSON 형식 권장)
    key_events TEXT,      -- 주요 뉴스 및 이벤트
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE top20_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    sector TEXT,
    entry_price REAL,
    target_price REAL,
    stop_loss REAL,
    r_value REAL,
    momentum_score REAL, -- 모멘텀 점수 (0-100)
    discovery_reason TEXT,
    hard_filter_pass BOOLEAN,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE top3_final (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    selection_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    proof_10pct TEXT,      -- 10% 상승 논리 근거
    bear_scenarios TEXT,   -- 하락 시나리오 및 반박 (JSON)
    price_strategy TEXT,   -- 상세 가격 전략
    status TEXT DEFAULT 'ACTIVE', -- ACTIVE, CLOSED
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE audit_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    is_top3 BOOLEAN,       -- Top3 여부
    entry_price REAL,
    max_price_reached REAL,
    min_price_reached REAL,
    final_return REAL,
    success_fail TEXT,     -- SUCCESS, FAIL, MISSED_GIANT
    error_analysis TEXT,   -- 실패/기회손실 원인 분석
    logic_tuning_rule TEXT, -- 신규 생성/수정된 룰 ID
    audit_date DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE growth_rules (
    rule_id TEXT PRIMARY KEY,
    category TEXT,         -- FILTER, MOMENTUM, RISK, SECTOR
    rule_description TEXT,
    origin_case_symbol TEXT, -- 해당 룰이 생성된 계기가 된 종목
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
