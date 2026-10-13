CREATE TABLE IF NOT EXISTS trade_flows (
    reporter_code INTEGER NOT NULL,
    reporter_name TEXT,
    partner_code  INTEGER NOT NULL,
    flow_code     TEXT    NOT NULL,
    cmd_code      TEXT    NOT NULL,
    period        INTEGER NOT NULL,
    net_wgt_kg    DOUBLE PRECISION,
    value_usd     DOUBLE PRECISION,
    weight_source TEXT,
    loaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (reporter_code, partner_code, flow_code, cmd_code, period)
);