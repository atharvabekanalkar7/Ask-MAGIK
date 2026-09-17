# Skyline Telecom Business & Analytical Rules
Ask MAGIK - Phase 1 Foundation

This document defines formal calculation standards, dimensional mappings, and query constraints governing all analytical data extraction and future RAG reasoning at Skyline Telecom.

---

## 1. Customer Loss & Churn Counting
- **Rule 1.1 (Distinct Identification)**: A customer is classified as "lost" or "churned" when a record exists in `churn_events` (or `subscriber_profile.status = 'Churned'`).
- **Rule 1.2 (Aggregation Semantics)**: Always use `COUNT(DISTINCT customer_id)` when counting lost or churned subscribers. Never count raw rows blindly in `churn_events`, as customers may record multiple interactions or re-entries.
- **Rule 1.3 (Early-Life Churn Definition)**: Early customer loss is strictly defined as churn occurring within $\le$ 3 months (or $\le$ 90 days) of activation, calculated by filtering `subscriber_profile.tenure_months <= 3` or evaluating `churn_date - activation_date <= 90`.

## 2. Product & Plan Classification
- **Rule 2.1 (Prepaid Plans)**: The following plans are strictly categorized as Prepaid:
  - `FlexMax 199`
  - `FlexMax 299`
  - `DataPlus 249`
  - `SmartTalk 199`
- **Rule 2.2 (Postpaid Plans)**: The following plans are strictly categorized as Postpaid:
  - `UltraData 399`
  - `BusinessPro 599`
- **Rule 2.3 (Classification Logic)**:
  ```sql
  CASE 
    WHEN plan IN ('UltraData 399', 'BusinessPro 599') THEN 'Postpaid'
    ELSE 'Prepaid'
  END AS plan_type
  ```

## 3. Geographic & Demographic Dimensions
- **Rule 3.1 (Geographic Region)**: Region is sourced exclusively from `subscriber_profile.region`. Valid regions are: `North`, `South`, `East`, `West`, and `Central`.
- **Rule 3.2 (Customer Segment)**: Customer segment is sourced exclusively from `subscriber_profile.segment`. Valid segments are: `Value`, `Standard`, `Premium`, and `High Value`.
- **Rule 3.3 (Customer Type)**: Sourced from `subscriber_profile.customer_type`. Valid values are: `Consumer` and `Small Business`.

## 4. Usage Trend & Decline Analysis
- **Rule 4.1 (Equivalent Periods)**: When measuring usage decline (e.g. "dropped > 30% in the last 60 days"), always compare two equal, consecutive observation windows:
  - Current window: Day $t-29$ to Day $t$ (30 days)
  - Prior window: Day $t-59$ to Day $t-30$ (30 days)
- **Rule 4.2 (Metric Standardization)**: Usage decline can be evaluated on daily average data volume (`data_mb`) or total data consumption over the window.
- **Rule 4.3 (Decline Threshold)**:
  $$\text{Decline \%} = \frac{\text{Prior Usage} - \text{Current Usage}}{\text{Prior Usage}} > 0.30$$

## 5. Marketing Campaign Performance
- **Rule 5.1 (Exposure vs. Response)**: Total rows in `campaign_response` represent campaign exposures (impressions/contacts).
- **Rule 5.2 (Response Condition)**: Only rows where `response = 'Responded'` represent successful conversions/engagements. Rows with `response = 'Not Responded'` represent non-conversions.
- **Rule 5.3 (Response Rate Formula)**:
  $$\text{Response Rate} = \frac{\text{COUNT(CASE WHEN response = 'Responded' THEN 1 END)} \times 100.0}{\text{COUNT(*)}}$$
- **Rule 5.4 (Annual Comparisons)**: When comparing seasonal campaigns like "Ramadan Data Bundle", filter by `campaign_name = 'Ramadan Data Bundle'` and group by year using `SUBSTR(campaign_date, 1, 4)` and `region`.

## 6. Financial Accounting & Revenue
- **Rule 6.1 (Distinction of Revenue Streams)**:
  - `billed_revenue`: Invoiced monthly charges (accrual basis).
  - `collected_revenue`: Actual cash receipts collected (cash basis).
  - Analytical questions requesting "revenue" without qualification default to `billed_revenue` for top-line size, or `collected_revenue` for cash performance.
- **Rule 6.2 (Collection Rate)**:
  $$\text{Collection Efficiency} = \frac{\sum \text{collected\_revenue}}{\sum \text{billed\_revenue}} \times 100.0$$

## 7. Data Privacy (PII) Constraints
- **Rule 7.1 (Zero PII)**: No personally identifiable information (customer names, phone numbers, email addresses, street addresses, national identity IDs) exists in the database.
- **Rule 7.2 (Anonymized Keys)**: `customer_id` (format: `CUST-xxxxx`) is the sole surrogate identifier.

## 8. Query Safety & Security
- **Rule 8.1 (Read-Only Execution)**: All analytical SQL queries generated for Ask MAGIK must be strictly `SELECT` queries. `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, or `TRUNCATE` operations are forbidden.
