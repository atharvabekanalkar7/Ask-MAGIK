# Skyline Telecom DataMart Entity Relationships
Ask MAGIK - Phase 1 Foundation

## Architecture Diagram

```
                 +----------------------+
                 |  subscriber_profile  |  (Central Dimension: 1 row per customer)
                 +----------+-----------+
                            |
       +--------------------+--------------------+--------------------+
       |                    |                    |                    |
       v                    v                    v                    v
+--------------+   +-------------------+   +-----------------+   +--------------+
| usage_daily  |   | campaign_response |   | revenue_monthly |   | churn_events |
+--------------+   +-------------------+   +-----------------+   +--------------+
(Daily Usage)      (Campaign Responses)    (Monthly Revenue)     (Churn Events)
```

---

## 1. Valid Joins

### Join Pattern 1: `subscriber_profile` $\leftrightarrow$ `usage_daily`
- **Join Condition**: `subscriber_profile.customer_id = usage_daily.customer_id`
- **Relationship**: One-to-Many (1:N)
- **Analytical Intent**: Calculate average data/voice/SMS consumption by region, segment, plan, or customer type.
- **Join Type**:
  - `INNER JOIN`: When analyzing usage strictly for customers with active daily records.
  - `LEFT JOIN`: When calculating overall population metrics where customers with zero usage must still be counted.

### Join Pattern 2: `subscriber_profile` $\leftrightarrow$ `campaign_response`
- **Join Condition**: `subscriber_profile.customer_id = campaign_response.customer_id`
- **Relationship**: One-to-Many (1:N)
- **Analytical Intent**: Evaluate campaign response rate and offer acceptance across geographic regions, customer types, or tenure cohorts.
- **Join Type**: `INNER JOIN` or `LEFT JOIN` depending on whether targeting exposed vs entire base.

### Join Pattern 3: `subscriber_profile` $\leftrightarrow$ `revenue_monthly`
- **Join Condition**: `subscriber_profile.customer_id = revenue_monthly.customer_id`
- **Relationship**: One-to-Many (1:N)
- **Analytical Intent**: Measure ARPU, billed revenue, and collected revenue sliced by customer attributes (segment, region, plan).
- **Join Type**: `INNER JOIN` for revenue trend analysis.

### Join Pattern 4: `subscriber_profile` $\leftrightarrow$ `churn_events`
- **Join Condition**: `subscriber_profile.customer_id = churn_events.customer_id`
- **Relationship**: One-to-One or One-to-Many (1:N)
- **Analytical Intent**: Determine customer loss rates across plan types (e.g. prepaid vs postpaid), regions, and channels.
- **Join Type**:
  - `INNER JOIN`: To analyze churn reasons and channels of customers who churned.
  - `LEFT JOIN`: When calculating churn rates against the total active subscriber denominator.

---

## 2. Joins Requiring Aggregation or CTEs (Cartesian Prevention)

> [!WARNING]
> Directly joining two child fact tables together (e.g. `usage_daily` joined directly to `revenue_monthly` or `campaign_response` joined to `churn_events`) without aggregating them first will cause a **Cartesian product explosion**, multiplying row counts and distorting numerical sums.

### Correct Pattern for Multi-Fact Analysis:
Always aggregate at the `customer_id` level inside Common Table Expressions (CTEs) or subqueries before joining:

```sql
WITH customer_avg_usage AS (
    SELECT customer_id, AVG(data_mb) AS avg_daily_data
    FROM usage_daily
    GROUP BY customer_id
),
customer_total_revenue AS (
    SELECT customer_id, SUM(collected_revenue) AS total_revenue
    FROM revenue_monthly
    GROUP BY customer_id
)
SELECT 
    s.customer_id,
    s.segment,
    u.avg_daily_data,
    r.total_revenue
FROM subscriber_profile s
LEFT JOIN customer_avg_usage u ON s.customer_id = u.customer_id
LEFT JOIN customer_total_revenue r ON s.customer_id = r.customer_id;
```
