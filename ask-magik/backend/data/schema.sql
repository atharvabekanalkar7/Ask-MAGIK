-- Skyline Telecom DataMart Schema (Phase 1)
-- Compatible with SQLite and PostgreSQL

CREATE TABLE IF NOT EXISTS subscriber_profile (
    customer_id VARCHAR(32) PRIMARY KEY,
    plan VARCHAR(64) NOT NULL,
    region VARCHAR(32) NOT NULL,
    tenure_months INTEGER NOT NULL,
    segment VARCHAR(32) NOT NULL,
    customer_type VARCHAR(32) NOT NULL,
    activation_date DATE NOT NULL,
    status VARCHAR(32) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_subscriber_plan ON subscriber_profile(plan);
CREATE INDEX IF NOT EXISTS idx_subscriber_region ON subscriber_profile(region);
CREATE INDEX IF NOT EXISTS idx_subscriber_segment ON subscriber_profile(segment);
CREATE INDEX IF NOT EXISTS idx_subscriber_type ON subscriber_profile(customer_type);
CREATE INDEX IF NOT EXISTS idx_subscriber_status ON subscriber_profile(status);
CREATE INDEX IF NOT EXISTS idx_subscriber_activation ON subscriber_profile(activation_date);

CREATE TABLE IF NOT EXISTS usage_daily (
    usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id VARCHAR(32) NOT NULL,
    usage_date DATE NOT NULL,
    voice_minutes REAL NOT NULL DEFAULT 0.0,
    data_mb REAL NOT NULL DEFAULT 0.0,
    sms_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES subscriber_profile(customer_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_usage_customer ON usage_daily(customer_id);
CREATE INDEX IF NOT EXISTS idx_usage_date ON usage_daily(usage_date);
CREATE INDEX IF NOT EXISTS idx_usage_customer_date ON usage_daily(customer_id, usage_date);

CREATE TABLE IF NOT EXISTS campaign_response (
    campaign_response_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id VARCHAR(32) NOT NULL,
    campaign_name VARCHAR(128) NOT NULL,
    campaign_date DATE NOT NULL,
    campaign_type VARCHAR(64) NOT NULL,
    response VARCHAR(32) NOT NULL,
    offer_value REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (customer_id) REFERENCES subscriber_profile(customer_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_campaign_customer ON campaign_response(customer_id);
CREATE INDEX IF NOT EXISTS idx_campaign_name ON campaign_response(campaign_name);
CREATE INDEX IF NOT EXISTS idx_campaign_date ON campaign_response(campaign_date);
CREATE INDEX IF NOT EXISTS idx_campaign_type ON campaign_response(campaign_type);
CREATE INDEX IF NOT EXISTS idx_campaign_response ON campaign_response(response);

CREATE TABLE IF NOT EXISTS revenue_monthly (
    revenue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id VARCHAR(32) NOT NULL,
    revenue_month VARCHAR(7) NOT NULL,
    billed_revenue REAL NOT NULL DEFAULT 0.0,
    collected_revenue REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (customer_id) REFERENCES subscriber_profile(customer_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_revenue_customer ON revenue_monthly(customer_id);
CREATE INDEX IF NOT EXISTS idx_revenue_month ON revenue_monthly(revenue_month);
CREATE INDEX IF NOT EXISTS idx_revenue_customer_month ON revenue_monthly(customer_id, revenue_month);

CREATE TABLE IF NOT EXISTS churn_events (
    churn_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id VARCHAR(32) NOT NULL,
    churn_date DATE NOT NULL,
    churn_reason VARCHAR(64) NOT NULL,
    churn_channel VARCHAR(64) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES subscriber_profile(customer_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_churn_customer ON churn_events(customer_id);
CREATE INDEX IF NOT EXISTS idx_churn_date ON churn_events(churn_date);
CREATE INDEX IF NOT EXISTS idx_churn_reason ON churn_events(churn_reason);
CREATE INDEX IF NOT EXISTS idx_churn_channel ON churn_events(churn_channel);
