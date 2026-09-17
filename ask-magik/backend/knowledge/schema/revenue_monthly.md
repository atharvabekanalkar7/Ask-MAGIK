# Table Schema: `revenue_monthly`

## Table Name
`revenue_monthly`

## Purpose
Contains monthly customer-level billing and cash collection records for financial accounting, trend tracking, and revenue assurance.

## Row Granularity
One row per subscriber per billing month.

## Columns

| Column Name | Data Type | Nullable | Description | Allowed / Example Values |
|-------------|-----------|----------|-------------|--------------------------|
| `revenue_id` | INTEGER | NO | Surrogate primary key (auto-incrementing) | `1`, `2`, `78000` |
| `customer_id` | VARCHAR(32) | NO | Invoiced customer identifier | Foreign key referencing `subscriber_profile.customer_id` |
| `revenue_month` | VARCHAR(7) | NO | Invoicing month in standard format | `'2026-01'` to `'2026-08'` |
| `billed_revenue` | REAL / FLOAT | NO | Total invoiced charges for the month (plan + addons) | `199.0` to `750.0` |
| `collected_revenue` | REAL / FLOAT | NO | Realized payment collected from subscriber | `150.0` to `750.0` |

## Primary Key
`revenue_id`

## Foreign Keys
- `customer_id` $\rightarrow$ `subscriber_profile(customer_id)` (ON DELETE CASCADE)

## Useful Relationships
- Many-to-One with `subscriber_profile` via `customer_id`

## Common Analytical Use Cases
1. Tracking month-over-month total collected revenue and billed revenue trends.
2. Calculating ARPU (Average Revenue Per User) by segment, plan, or region.
3. Calculating collection efficiency ratio: `SUM(collected_revenue) / SUM(billed_revenue)`.
4. Identifying revenue leakage or non-paying customer groups.
