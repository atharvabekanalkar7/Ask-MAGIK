"""
Acceptance Test Script - Runs the 5 Core Analytical Questions
Ask MAGIK - Phase 1 Foundation
"""

from tabulate import tabulate  # fallback if tabulate isn't present
from sqlalchemy import text
from backend.database.connection import engine

QUERIES = [
    (
        "Question 1: Which prepaid plans had the highest customer loss in the western region last month?",
        """
        SELECT 
            s.plan, 
            COUNT(DISTINCT c.customer_id) AS customer_loss
        FROM churn_events c
        JOIN subscriber_profile s ON c.customer_id = s.customer_id
        WHERE s.region = 'West'
          AND s.plan IN ('FlexMax 199', 'FlexMax 299', 'DataPlus 249', 'SmartTalk 199')
          AND c.churn_date >= '2026-08-01' AND c.churn_date <= '2026-08-31'
        GROUP BY s.plan
        ORDER BY customer_loss DESC;
        """
    ),
    (
        "Question 2: How many customers churned by region?",
        """
        SELECT 
            s.region, 
            COUNT(DISTINCT c.customer_id) AS churned_customers
        FROM churn_events c
        JOIN subscriber_profile s ON c.customer_id = s.customer_id
        GROUP BY s.region
        ORDER BY churned_customers DESC;
        """
    ),
    (
        "Question 3: Which campaign had the highest response rate?",
        """
        SELECT 
            campaign_name, 
            campaign_type,
            COUNT(*) AS total_exposures,
            COUNT(CASE WHEN response = 'Responded' THEN 1 END) AS responses,
            ROUND(COUNT(CASE WHEN response = 'Responded' THEN 1 END) * 100.0 / COUNT(*), 2) AS response_rate_pct
        FROM campaign_response
        GROUP BY campaign_name, campaign_type
        ORDER BY response_rate_pct DESC;
        """
    ),
    (
        "Question 4: Which customer segment has the highest average data usage?",
        """
        SELECT 
            s.segment, 
            ROUND(AVG(u.data_mb), 2) AS avg_daily_data_mb,
            ROUND(AVG(u.voice_minutes), 2) AS avg_daily_voice_minutes
        FROM subscriber_profile s
        JOIN usage_daily u ON s.customer_id = u.customer_id
        GROUP BY s.segment
        ORDER BY avg_daily_data_mb DESC;
        """
    ),
    (
        "Question 5: How has collected revenue changed by month?",
        """
        SELECT 
            revenue_month, 
            ROUND(SUM(billed_revenue), 2) AS total_billed, 
            ROUND(SUM(collected_revenue), 2) AS total_collected,
            ROUND(SUM(collected_revenue) * 100.0 / SUM(billed_revenue), 2) AS collection_efficiency_pct
        FROM revenue_monthly
        GROUP BY revenue_month
        ORDER BY revenue_month ASC;
        """
    ),
]


def print_table(headers, rows):
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header_str = "| " + " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"

    print(sep)
    print(header_str)
    print(sep)
    for row in rows:
        row_str = "| " + " | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)) + " |"
        print(row_str)
    print(sep)


def main():
    print("=" * 80)
    print("ASK MAGIK - PHASE 1 ACCEPTANCE TEST QUERIES")
    print("=" * 80)

    with engine.connect() as conn:
        for title, query in QUERIES:
            print(f"\n>>> {title}")
            print("-" * 80)
            res = conn.execute(text(query))
            headers = list(res.keys())
            rows = res.fetchall()
            print_table(headers, rows)


if __name__ == "__main__":
    main()
