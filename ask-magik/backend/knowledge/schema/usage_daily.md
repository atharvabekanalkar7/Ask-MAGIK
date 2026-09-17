# Table Schema: `usage_daily`

## Table Name
`usage_daily`

## Purpose
Records daily network service consumption (voice, mobile broadband data, and text messaging) for each subscriber across historical timeframes.

## Row Granularity
One row per customer per calendar day.

## Columns

| Column Name | Data Type | Nullable | Description | Allowed / Example Values |
|-------------|-----------|----------|-------------|--------------------------|
| `usage_id` | INTEGER | NO | Surrogate primary key (auto-incrementing) | `1`, `2`, `105432` |
| `customer_id` | VARCHAR(32) | NO | Customer identifier | Foreign key referencing `subscriber_profile.customer_id` |
| `usage_date` | DATE | NO | Calendar date of recorded consumption | `'2026-05-24'` to `'2026-08-31'` |
| `voice_minutes` | REAL / FLOAT | NO | Total duration of outgoing voice calls in minutes | `0.0` to `120.0` |
| `data_mb` | REAL / FLOAT | NO | Total data volume downloaded/uploaded in megabytes | `0.0` to `8500.0` |
| `sms_count` | INTEGER | NO | Total number of SMS messages sent | `0` to `25` |

## Primary Key
`usage_id`

## Foreign Keys
- `customer_id` $\rightarrow$ `subscriber_profile(customer_id)` (ON DELETE CASCADE)

## Useful Relationships
- Many-to-One with `subscriber_profile` via `customer_id`

## Common Analytical Use Cases
1. Tracking average daily or monthly data volume (MB) by customer segment or customer type.
2. Detecting usage drops/declines across observation windows (e.g. trailing 30 days vs prior 30 days).
3. Analyzing heavy data consumers (High Value / Small Business) for network capacity and cross-sell.
4. Correlating pre-churn usage dormancy or sudden drops with churn probability.
