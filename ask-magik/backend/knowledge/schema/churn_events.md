# Table Schema: `churn_events`

## Table Name
`churn_events`

## Purpose
Records individual subscriber churn and service termination events, capturing specific termination reasons and the channel through which the disconnection was processed.

## Row Granularity
One row per customer cancellation event.

## Columns

| Column Name | Data Type | Nullable | Description | Allowed / Example Values |
|-------------|-----------|----------|-------------|--------------------------|
| `churn_event_id` | INTEGER | NO | Surrogate primary key (auto-incrementing) | `1`, `2`, `1200` |
| `customer_id` | VARCHAR(32) | NO | Churned customer identifier | Foreign key referencing `subscriber_profile.customer_id` |
| `churn_date` | DATE | NO | Date service termination occurred | `'2026-05-24'` to `'2026-08-31'` |
| `churn_reason` | VARCHAR(64) | NO | Customer or agent cited driver for cancellation | `'Price'`, `'Poor Service'`, `'Competitor'`, `'Low Usage'`, `'Offer Expired'`, `'Customer Choice'` |
| `churn_channel` | VARCHAR(64) | NO | Touchpoint where cancellation was submitted | `'Retail'`, `'Digital'`, `'Call Center'`, `'Partner'`, `'App'` |

## Primary Key
`churn_event_id`

## Foreign Keys
- `customer_id` $\rightarrow$ `subscriber_profile(customer_id)` (ON DELETE CASCADE)

## Useful Relationships
- Many-to-One with `subscriber_profile` via `customer_id`

## Common Analytical Use Cases
1. Counting customer loss by region, plan, tenure cohort, or customer type.
2. Identifying top churn reasons to isolate root causes (e.g. Price vs Poor Service).
3. Analyzing early-life churn concentration across channels (e.g. Digital vs Retail).
4. Monitoring time-series churn trends (e.g. spikes in the last month in specific regions).
