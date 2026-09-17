# Skyline Telecom Business Glossary (Ask MAGIK Knowledge Base)

This glossary defines standard telecom business terms, KPI formulas, data lineage, and calculation rules used by the Ask MAGIK AI platform. It serves as semantic grounding for RAG and SQL translation.

---

## 1. Active Customer
- **Business meaning**: A customer who has an active service subscription with Skyline Telecom and has not churned.
- **Primary table**: `subscriber_profile`
- **Key field**: `status`
- **Calculation rule**: `WHERE status = 'Active'` or `WHERE status != 'Churned'`.

---

## 2. Customer Loss
- **Business meaning**: A subscriber who has voluntarily or involuntarily disconnected their service and left Skyline Telecom.
- **Primary table**: `churn_events` (or `subscriber_profile` where `status = 'Churned'`)
- **Key field**: `customer_id`
- **Date field**: `churn_date`
- **Calculation rule**: Always compute `COUNT(DISTINCT customer_id)` from `churn_events` within the target evaluation window. Do not count raw rows blindly.

---

## 3. Churn
- **Business meaning**: The state or event of a customer terminating their relationship with Skyline Telecom.
- **Primary table**: `churn_events`
- **Key field**: `customer_id`, `churn_reason`, `churn_channel`
- **Date field**: `churn_date`
- **Calculation rule**: Churn rate is calculated as:
  $$\text{Churn Rate} = \frac{\text{Count of distinct churned customers in period}}{\text{Total active customers at start of period}} \times 100\%$$

---

## 4. Early-Life Churn
- **Business meaning**: Customer attrition occurring within the initial period of subscription (defined at Skyline as tenure $\le$ 3 months or $\le$ 90 days / 1 quarter). Indicates onboarding, expectation mismatch, or network quality friction.
- **Primary table**: `churn_events` joined with `subscriber_profile`
- **Key fields**: `subscriber_profile.tenure_months`, `churn_events.churn_date`, `churn_events.churn_channel`
- **Date field**: `churn_events.churn_date`
- **Calculation rule**: Filter `churn_events` joined to `subscriber_profile` on `subscriber_profile.tenure_months <= 3` (or evaluate difference between `churn_events.churn_date` and `subscriber_profile.activation_date` $\le$ 90 days).

---

## 5. Prepaid
- **Business meaning**: Customers who pay for telecommunications services upfront prior to consumption without a recurring monthly contract bill.
- **Primary table**: `subscriber_profile`
- **Key field**: `plan`
- **Calculation rule**: Filter `plan IN ('FlexMax 199', 'FlexMax 299', 'DataPlus 249', 'SmartTalk 199')`.

---

## 6. Postpaid
- **Business meaning**: Customers who receive services on an ongoing monthly contract and are billed at the end of each billing cycle based on their plan and out-of-bundle charges.
- **Primary table**: `subscriber_profile`
- **Key field**: `plan`
- **Calculation rule**: Filter `plan IN ('UltraData 399', 'BusinessPro 599')` or `plan NOT IN ('FlexMax 199', 'FlexMax 299', 'DataPlus 249', 'SmartTalk 199')`.

---

## 7. Small Business
- **Business meaning**: Commercial enterprise accounts with higher volume voice and data consumption, categorized under B2B accounts.
- **Primary table**: `subscriber_profile`
- **Key field**: `customer_type`
- **Calculation rule**: `WHERE customer_type = 'Small Business'`.

---

## 8. Consumer
- **Business meaning**: Individual retail end-users subscribing for personal and domestic usage.
- **Primary table**: `subscriber_profile`
- **Key field**: `customer_type`
- **Calculation rule**: `WHERE customer_type = 'Consumer'`.

---

## 9. ARPU (Average Revenue Per User)
- **Business meaning**: The average revenue generated per active subscriber over a specified time interval (typically monthly).
- **Primary tables**: `revenue_monthly` joined with `subscriber_profile`
- **Key fields**: `revenue_monthly.billed_revenue` (or `collected_revenue`), `subscriber_profile.customer_id`
- **Date field**: `revenue_monthly.revenue_month`
- **Calculation rule**:
  $$\text{ARPU} = \frac{\sum \text{billed\_revenue}}{\text{COUNT(DISTINCT customer\_id)}}$$

---

## 10. Revenue
- **Business meaning**: Total monetary value recognized by Skyline Telecom from telecom services, subscriptions, data bundles, and usage.
- **Primary table**: `revenue_monthly`
- **Key fields**: `billed_revenue`, `collected_revenue`
- **Date field**: `revenue_month`
- **Calculation rule**: Specify whether analyzing invoiced financial accrual (`billed_revenue`) or realized cash receipts (`collected_revenue`).

---

## 11. Billed Revenue
- **Business meaning**: The total invoiced amount charged to the subscriber for a given billing month, including fixed plan rate and extra usage charges.
- **Primary table**: `revenue_monthly`
- **Key field**: `billed_revenue`
- **Date field**: `revenue_month`
- **Calculation rule**: `SUM(billed_revenue)` grouped by time period, plan, or segment.

---

## 12. Collected Revenue
- **Business meaning**: The actual cash payments received by Skyline Telecom from subscribers against billed invoices.
- **Primary table**: `revenue_monthly`
- **Key field**: `collected_revenue`
- **Date field**: `revenue_month`
- **Calculation rule**: `SUM(collected_revenue)`. Collection efficiency ratio is calculated as `SUM(collected_revenue) / SUM(billed_revenue)`.

---

## 13. Campaign Response
- **Business meaning**: A record indicating whether a customer targeted with a promotional or informational marketing communication responded favorably or accepted the offer.
- **Primary table**: `campaign_response`
- **Key fields**: `campaign_name`, `response`, `offer_value`, `campaign_type`
- **Date field**: `campaign_date`
- **Calculation rule**: Response Rate is:
  $$\text{Response Rate} = \frac{\text{COUNT(CASE WHEN response = 'Responded' THEN 1 END)}}{\text{COUNT(*)}} \times 100\%$$

---

## 14. Retention Campaign
- **Business meaning**: Targeted marketing initiatives aimed specifically at at-risk subscribers to prevent churn and encourage plan renewal or loyalty.
- **Primary table**: `campaign_response`
- **Key fields**: `campaign_type = 'Retention'`, `campaign_name IN ('Summer Saver', 'Winback Offer')`
- **Date field**: `campaign_date`
- **Calculation rule**: Filter by `campaign_type = 'Retention'`.

---

## 15. Usage Decline
- **Business meaning**: A substantial reduction in subscriber data MB, voice minutes, or SMS over two equivalent sequential or comparative observation windows (e.g. comparing the most recent 30-day window to the preceding 30-day window).
- **Primary table**: `usage_daily`
- **Key fields**: `data_mb`, `voice_minutes`, `usage_date`, `customer_id`
- **Date field**: `usage_date`
- **Calculation rule**: Compute average or sum of metric in Period 2 versus Period 1:
  $$\text{Decline \%} = \frac{\text{Usage}_{\text{Period 1}} - \text{Usage}_{\text{Period 2}}}{\text{Usage}_{\text{Period 1}}} \times 100\%$$
  Filter where $\text{Decline \%} > 30\%$.

---

## 16. Customer Segment
- **Business meaning**: Classification of customers according to their value contribution and consumption tier: `Value`, `Standard`, `Premium`, `High Value`.
- **Primary table**: `subscriber_profile`
- **Key field**: `segment`
- **Calculation rule**: `GROUP BY segment`.

---

## 17. Regional Churn
- **Business meaning**: Distribution of customer loss broken down across geographical operating territories (`North`, `South`, `East`, `West`, `Central`).
- **Primary tables**: `churn_events` joined with `subscriber_profile` on `customer_id`
- **Key fields**: `subscriber_profile.region`, `churn_events.customer_id`
- **Date field**: `churn_events.churn_date`
- **Calculation rule**:
  ```sql
  SELECT s.region, COUNT(DISTINCT c.customer_id) AS lost_customers
  FROM churn_events c
  JOIN subscriber_profile s ON c.customer_id = s.customer_id
  GROUP BY s.region;
  ```
