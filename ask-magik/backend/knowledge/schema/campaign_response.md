# Table Schema: `campaign_response`

## Table Name
`campaign_response`

## Purpose
Captures marketing campaign exposures, promotional offers, and whether the targeted subscriber accepted or responded to the offer.

## Row Granularity
One row per campaign contact / impression delivered to a customer.

## Columns

| Column Name | Data Type | Nullable | Description | Allowed / Example Values |
|-------------|-----------|----------|-------------|--------------------------|
| `campaign_response_id` | INTEGER | NO | Surrogate primary key (auto-incrementing) | `1`, `2`, `45000` |
| `customer_id` | VARCHAR(32) | NO | Targeted customer identifier | Foreign key referencing `subscriber_profile.customer_id` |
| `campaign_name` | VARCHAR(128) | NO | Name of marketing initiative | `'Ramadan Data Bundle'`, `'Weekend Booster'`, `'Summer Saver'`, `'Loyalty Upgrade'`, `'Winback Offer'`, `'5G Upgrade'` |
| `campaign_date` | DATE | NO | Date the campaign offer was sent | `'2025-03-20'`, `'2026-03-15'` |
| `campaign_type` | VARCHAR(64) | NO | Strategic category of marketing action | `'Data'`, `'Voice'`, `'Loyalty'`, `'Retention'`, `'Upgrade'` |
| `response` | VARCHAR(32) | NO | Customer conversion outcome | `'Responded'`, `'Not Responded'` |
| `offer_value` | REAL / FLOAT | NO | Nominal monetary or bundle value of incentive | `25.0`, `50.0`, `60.0`, `100.0` |

## Primary Key
`campaign_response_id`

## Foreign Keys
- `customer_id` $\rightarrow$ `subscriber_profile(customer_id)` (ON DELETE CASCADE)

## Useful Relationships
- Many-to-One with `subscriber_profile` via `customer_id`

## Common Analytical Use Cases
1. Measuring conversion and response rates by campaign name, type, and customer segment.
2. Comparing seasonal campaigns year-over-year (e.g. Ramadan Data Bundle in 2025 vs 2026 across regions).
3. Evaluating effectiveness of Retention campaigns (`Summer Saver`, `Winback Offer`) against subsequent churn events.
