# Table Schema: `subscriber_profile`

## Table Name
`subscriber_profile`

## Purpose
Serves as the central customer dimension in the Skyline Telecom DataMart. It stores demographic, subscription plan, lifecycle status, tenure, and segmentation attributes for all customers.

## Row Granularity
One row per individual subscriber account.

## Columns

| Column Name | Data Type | Nullable | Description | Allowed / Example Values |
|-------------|-----------|----------|-------------|--------------------------|
| `customer_id` | VARCHAR(32) | NO | Unique surrogate customer identifier | `'CUST-00001'`, `'CUST-05421'` |
| `plan` | VARCHAR(64) | NO | Name of current tariff plan | `'FlexMax 199'`, `'FlexMax 299'`, `'DataPlus 249'`, `'SmartTalk 199'`, `'UltraData 399'`, `'BusinessPro 599'` |
| `region` | VARCHAR(32) | NO | Operating geographic sales territory | `'North'`, `'South'`, `'East'`, `'West'`, `'Central'` |
| `tenure_months` | INTEGER | NO | Number of completed months as an active subscriber | `1` to `48` |
| `segment` | VARCHAR(32) | NO | Strategic value tier based on historical spend/ARPU | `'Value'`, `'Standard'`, `'Premium'`, `'High Value'` |
| `customer_type` | VARCHAR(32) | NO | Line of business categorization | `'Consumer'`, `'Small Business'` |
| `activation_date` | DATE | NO | Date the subscriber initially activated service | `'2024-05-12'`, `'2026-02-01'` |
| `status` | VARCHAR(32) | NO | Current account status | `'Active'`, `'Churned'` |

## Primary Key
`customer_id`

## Foreign Keys
None (root customer dimension).

## Useful Relationships
- One-to-Many with `usage_daily` via `customer_id`
- One-to-Many with `campaign_response` via `customer_id`
- One-to-Many with `revenue_monthly` via `customer_id`
- One-to-Many with `churn_events` via `customer_id`

## Common Analytical Use Cases
1. Segmenting customer counts by region and plan type.
2. Filtering active vs churned customer populations.
3. Calculating base subscriber distribution across Consumer vs Small Business.
4. Identifying early tenure cohorts ($\le 3$ or $\le 6$ months) for onboarding analysis.
