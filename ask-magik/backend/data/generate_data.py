"""
Synthetic Data Generator for Skyline Telecom DataMart
Ask MAGIK - Phase 1 Foundation

Generates realistic synthetic data for:
- 10,000 subscribers in subscriber_profile
- ~1,000,000 daily usage records (100 days)
- ~100,000 campaign responses (including Ramadan campaign over 2 years across regions)
- ~80,000 monthly revenue records (8 months)
- ~1,200 churn events with realistic probabilistic drivers

Engineered so that all 4 demo questions yield meaningful analytical patterns.
"""

import random
from datetime import date, timedelta
from typing import Dict, List, Tuple, Any

# Fixed random seed for deterministic yet realistic synthetic generation
RANDOM_SEED = 42

# Master reference timeline (Anchored at 2026-08-31)
ANCHOR_DATE = date(2026, 8, 31)
HISTORICAL_DAYS = 100
START_DATE = ANCHOR_DATE - timedelta(days=HISTORICAL_DAYS - 1)  # 2026-05-24

# Dimension values
REGIONS = ["North", "South", "East", "West", "Central"]
REGION_WEIGHTS = [0.25, 0.20, 0.20, 0.20, 0.15]

PREPAID_PLANS = ["FlexMax 199", "FlexMax 299", "DataPlus 249", "SmartTalk 199"]
POSTPAID_PLANS = ["UltraData 399", "BusinessPro 599"]
ALL_PLANS = PREPAID_PLANS + POSTPAID_PLANS

CUSTOMER_TYPES = ["Consumer", "Small Business"]
CUSTOMER_TYPE_WEIGHTS = [0.82, 0.18]

SEGMENTS = ["Value", "Standard", "Premium", "High Value"]
SEGMENT_WEIGHTS = [0.40, 0.35, 0.18, 0.07]

CHURN_REASONS = ["Price", "Poor Service", "Competitor", "Low Usage", "Offer Expired", "Customer Choice"]
CHURN_CHANNELS = ["Retail", "Digital", "Call Center", "Partner", "App"]

CAMPAIGN_NAMES = [
    "Ramadan Data Bundle",
    "Weekend Booster",
    "Summer Saver",
    "Loyalty Upgrade",
    "Winback Offer",
    "5G Upgrade",
]

CAMPAIGN_TYPE_MAP = {
    "Ramadan Data Bundle": "Data",
    "Weekend Booster": "Data",
    "Summer Saver": "Retention",
    "Loyalty Upgrade": "Loyalty",
    "Winback Offer": "Retention",
    "5G Upgrade": "Upgrade",
}


def generate_subscribers(num_customers: int = 10000) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Generates subscriber profiles.
    Returns:
        subscribers: list of dicts for subscriber_profile table.
        sub_lookup: lookup map keyed by customer_id for fast referencing.
    """
    random.seed(RANDOM_SEED)
    subscribers = []
    sub_lookup = {}

    for i in range(1, num_customers + 1):
        cust_id = f"CUST-{i:05d}"
        cust_type = random.choices(CUSTOMER_TYPES, weights=CUSTOMER_TYPE_WEIGHTS)[0]

        # Small Business only gets BusinessPro 599 (75%) or UltraData 399 (25%)
        if cust_type == "Small Business":
            plan = random.choices(["BusinessPro 599", "UltraData 399"], weights=[0.75, 0.25])[0]
            segment = random.choices(["Standard", "Premium", "High Value"], weights=[0.20, 0.50, 0.30])[0]
        else:
            plan = random.choices(
                ["FlexMax 199", "FlexMax 299", "DataPlus 249", "SmartTalk 199", "UltraData 399"],
                weights=[0.30, 0.25, 0.20, 0.15, 0.10],
            )[0]
            segment = random.choices(SEGMENTS, weights=SEGMENT_WEIGHTS)[0]

        region = random.choices(REGIONS, weights=REGION_WEIGHTS)[0]

        # Tenure: 1 to 48 months
        # For Demo Question 4 (rise in early customer loss), create a pool of low tenure customers
        if i % 5 == 0:
            tenure_months = random.randint(1, 6)
        else:
            tenure_months = random.randint(3, 48)

        # Activation date approximately corresponds to tenure
        activation_days_ago = tenure_months * 30 + random.randint(0, 25)
        activation_date = ANCHOR_DATE - timedelta(days=activation_days_ago)

        # Status: Initially Active, churn assignments will update to Churned
        status = "Active"

        sub_record = {
            "customer_id": cust_id,
            "plan": plan,
            "region": region,
            "tenure_months": tenure_months,
            "segment": segment,
            "customer_type": cust_type,
            "activation_date": activation_date,
            "status": status,
        }
        subscribers.append(sub_record)
        sub_lookup[cust_id] = sub_record

    return subscribers, sub_lookup


def generate_churn_events(
    subscribers: List[Dict[str, Any]],
    target_churn_count: int = 1200
) -> Tuple[List[Dict[str, Any]], set]:
    """
    Generates churn events matching realistic probabilistic drivers:
    - Higher churn for West region prepaid (FlexMax 199 & SmartTalk 199) in last month (Aug 2026).
    - Early customer loss (tenure <= 6 months) concentrated in Digital channel and Consumer type.
    """
    random.seed(RANDOM_SEED + 1)
    churn_events = []
    churned_customer_ids = set()

    # Score each customer for churn likelihood
    candidates = []
    for sub in subscribers:
        score = 1.0
        # West region prepaid bonus
        if sub["region"] == "West" and sub["plan"] in ["FlexMax 199", "SmartTalk 199"]:
            score *= 3.5
        # Early tenure bonus
        if sub["tenure_months"] <= 6:
            score *= 2.2
        if sub["segment"] == "Value":
            score *= 1.5
        elif sub["segment"] == "High Value":
            score *= 0.4
        candidates.append((score, sub))

    # Sort or weight selection
    weights = [c[0] for c in candidates]
    subs = [c[1] for c in candidates]

    # Select unique customers to churn
    selected_indices = set()
    while len(selected_indices) < target_churn_count:
        idx = random.choices(range(len(subs)), weights=weights, k=1)[0]
        selected_indices.add(idx)

    # Now create churn events for each selected customer
    for idx in selected_indices:
        sub = subs[idx]
        cust_id = sub["customer_id"]
        churned_customer_ids.add(cust_id)
        sub["status"] = "Churned"

        act_date = sub["activation_date"]
        # Determine churn date
        # If West region prepaid, high concentration in last month (2026-08-01 to 2026-08-31)
        if sub["region"] == "West" and sub["plan"] in ["FlexMax 199", "SmartTalk 199"] and random.random() < 0.65:
            churn_day = random.randint(1, 31)
            candidate_date = date(2026, 8, churn_day)
            churn_date = max(candidate_date, act_date + timedelta(days=1))
            churn_reason = random.choices(["Price", "Competitor"], weights=[0.6, 0.4])[0]
            churn_channel = random.choices(["Digital", "Retail", "App"], weights=[0.4, 0.3, 0.3])[0]
        # Early customer loss: concentrated in Digital channel, reason Price / Poor Service
        elif sub["tenure_months"] <= 6 and random.random() < 0.70:
            # Churned within the last 90 days (Quarter 3)
            max_days = max(1, (ANCHOR_DATE - act_date).days)
            days_offset = random.randint(1, min(90, max_days))
            churn_date = ANCHOR_DATE - timedelta(days=days_offset)
            if churn_date <= act_date:
                churn_date = act_date + timedelta(days=1)
            churn_channel = random.choices(["Digital", "App", "Call Center", "Retail"], weights=[0.55, 0.20, 0.15, 0.10])[0]
            churn_reason = random.choices(["Price", "Poor Service", "Low Usage"], weights=[0.50, 0.35, 0.15])[0]
        else:
            max_days = max(1, (ANCHOR_DATE - act_date).days)
            days_offset = random.randint(1, min(HISTORICAL_DAYS, max_days))
            churn_date = ANCHOR_DATE - timedelta(days=days_offset)
            if churn_date <= act_date:
                churn_date = act_date + timedelta(days=1)
            churn_reason = random.choices(CHURN_REASONS)[0]
            churn_channel = random.choices(CHURN_CHANNELS)[0]

        churn_events.append({
            "customer_id": cust_id,
            "churn_date": churn_date,
            "churn_reason": churn_reason,
            "churn_channel": churn_channel,
        })

    return churn_events, churned_customer_ids


def generate_usage_daily(
    subscribers: List[Dict[str, Any]],
    churn_lookup: Dict[str, date],
    num_declining_small_biz: int = 150,
) -> List[Dict[str, Any]]:
    """
    Generates daily usage rows for all subscribers across historical timeline.
    Special calibrations:
    - Small Business: 2.5x voice, 3.5x data.
    - Premium / High Value: significantly higher data usage.
    - Value segment: modest usage.
    - Question 3 calibration: dedicated subset of Postpaid Small Business customers
      whose usage drops > 30% in the last 60 days.
    """
    random.seed(RANDOM_SEED + 2)
    usage_rows = []

    # Identify eligible Postpaid Small Business customers for Question 3
    postpaid_sb = [
        s["customer_id"]
        for s in subscribers
        if s["customer_type"] == "Small Business" and s["plan"] in POSTPAID_PLANS
    ]
    random.shuffle(postpaid_sb)
    declining_sb_set = set(postpaid_sb[:num_declining_small_biz])

    # Date threshold for recent 30-day period (2026-08-02 through 2026-08-31)
    recent_period_start = date(2026, 8, 2)

    # Segment multipliers
    segment_mult = {
        "Value": (0.6, 0.5),        # (voice, data)
        "Standard": (1.0, 1.0),
        "Premium": (1.6, 2.8),
        "High Value": (2.2, 4.5),
    }

    for sub in subscribers:
        cust_id = sub["customer_id"]
        c_type = sub["customer_type"]
        seg = sub["segment"]
        churn_d = churn_lookup.get(cust_id)
        is_declining = cust_id in declining_sb_set

        s_voice, s_data = segment_mult.get(seg, (1.0, 1.0))
        base_voice = (35.0 if c_type == "Small Business" else 12.0) * s_voice
        base_data = (1200.0 if c_type == "Small Business" else 350.0) * s_data
        base_sms = 8 if c_type == "Small Business" else 4

        for d_idx in range(HISTORICAL_DAYS):
            cur_date = START_DATE + timedelta(days=d_idx)
            # Stop generating daily usage after churn date
            if churn_d and cur_date > churn_d:
                break

            # Handle declining small business logic for Question 3
            # Prior period (2026-07-03 to 2026-08-01): normal usage
            # Recent period (2026-08-02 to 2026-08-31): factor 0.35 - 0.55 relative to baseline
            if is_declining and cur_date >= recent_period_start:
                factor = random.uniform(0.35, 0.55)
            else:
                # Normal variation
                factor = random.uniform(0.70, 1.30)

            voice = round(max(0.0, base_voice * factor + random.gauss(0, 2.0)), 2)
            data = round(max(0.0, base_data * factor + random.gauss(0, 40.0)), 2)
            sms = max(0, int(base_sms * factor + random.choice([-1, 0, 1])))

            usage_rows.append({
                "customer_id": cust_id,
                "usage_date": cur_date,
                "voice_minutes": voice,
                "data_mb": data,
                "sms_count": sms,
            })

    return usage_rows


def generate_campaign_responses(
    subscribers: List[Dict[str, Any]],
    target_count: int = 100000
) -> List[Dict[str, Any]]:
    """
    Generates campaign response records.
    Calibrations:
    - Question 2: 'Ramadan Data Bundle' across two years (2025 and 2026) by region.
      2025 Ramadan campaign: ~2025-03-15 to 2025-04-15
      2026 Ramadan campaign: ~2026-03-10 to 2026-04-10
      Different response rates per region across years to provide clear comparative analytics.
    - Other campaigns distributed over the past year.
    """
    random.seed(RANDOM_SEED + 3)
    campaign_rows = []

    # 1. Dedicated Ramadan Data Bundle campaigns for Question 2
    # Regional baseline response rates:
    # 2025: North 18%, South 15%, East 22%, West 14%, Central 20%
    # 2026: North 25%, South 19%, East 29%, West 23%, Central 27%
    ramadan_rates_2025 = {"North": 0.18, "South": 0.15, "East": 0.22, "West": 0.14, "Central": 0.20}
    ramadan_rates_2026 = {"North": 0.25, "South": 0.19, "East": 0.29, "West": 0.23, "Central": 0.27}

    for sub in subscribers:
        cust_id = sub["customer_id"]
        region = sub["region"]

        # 2025 Campaign (if customer tenure >= 16 months)
        if sub["tenure_months"] >= 16 and random.random() < 0.60:
            c_date = date(2025, 3, random.randint(15, 30))
            prob = ramadan_rates_2025.get(region, 0.18)
            resp = "Responded" if random.random() < prob else "Not Responded"
            campaign_rows.append({
                "customer_id": cust_id,
                "campaign_name": "Ramadan Data Bundle",
                "campaign_date": c_date,
                "campaign_type": "Data",
                "response": resp,
                "offer_value": 50.0,
            })

        # 2026 Campaign (if customer tenure >= 5 months)
        if sub["tenure_months"] >= 5 and random.random() < 0.70:
            c_date = date(2026, 3, random.randint(10, 25))
            prob = ramadan_rates_2026.get(region, 0.24)
            resp = "Responded" if random.random() < prob else "Not Responded"
            campaign_rows.append({
                "customer_id": cust_id,
                "campaign_name": "Ramadan Data Bundle",
                "campaign_date": c_date,
                "campaign_type": "Data",
                "response": resp,
                "offer_value": 60.0,
            })

    # 2. General campaign distribution up to target_count
    remaining = target_count - len(campaign_rows)
    other_campaigns = [c for c in CAMPAIGN_NAMES if c != "Ramadan Data Bundle"]

    for _ in range(remaining):
        sub = random.choice(subscribers)
        c_name = random.choice(other_campaigns)
        c_type = CAMPAIGN_TYPE_MAP[c_name]
        days_ago = random.randint(10, 300)
        c_date = ANCHOR_DATE - timedelta(days=days_ago)

        # Response probability influenced by segment
        base_resp_prob = 0.15
        if sub["segment"] in ["Premium", "High Value"]:
            base_resp_prob = 0.25
        if c_name == "Summer Saver":
            base_resp_prob = 0.32  # High response rate for question demo

        resp = "Responded" if random.random() < base_resp_prob else "Not Responded"
        offer_val = random.choice([25.0, 50.0, 75.0, 100.0, 150.0])

        campaign_rows.append({
            "customer_id": sub["customer_id"],
            "campaign_name": c_name,
            "campaign_date": c_date,
            "campaign_type": c_type,
            "response": resp,
            "offer_value": offer_val,
        })

    return campaign_rows


def generate_revenue_monthly(
    subscribers: List[Dict[str, Any]],
    churn_lookup: Dict[str, date],
    months: List[str] = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]
) -> List[Dict[str, Any]]:
    """
    Generates monthly revenue records (8 months).
    Correlated loosely with customer plan price and segment.
    Shows realistic collected vs billed ratio (90% - 98%).
    """
    random.seed(RANDOM_SEED + 4)
    revenue_rows = []

    plan_base_cost = {
        "FlexMax 199": 199.0,
        "FlexMax 299": 299.0,
        "DataPlus 249": 249.0,
        "SmartTalk 199": 199.0,
        "UltraData 399": 399.0,
        "BusinessPro 599": 599.0,
    }

    for m in months:
        y, mon = map(int, m.split("-"))
        m_start = date(y, mon, 1)

        for sub in subscribers:
            cust_id = sub["customer_id"]
            churn_d = churn_lookup.get(cust_id)
            # If customer churned before this month, skip
            if churn_d and churn_d < m_start:
                continue

            base = plan_base_cost.get(sub["plan"], 200.0)
            # Add out-of-bundle variance
            extra = random.uniform(0.0, 0.25) * base
            billed = round(base + extra, 2)

            # Collection rate typically 90% - 99%, with slight unpaid bills
            collect_pct = random.uniform(0.90, 0.99)
            if random.random() < 0.04:  # occasional default / late payment
                collect_pct = random.uniform(0.50, 0.85)

            collected = round(billed * collect_pct, 2)

            revenue_rows.append({
                "customer_id": cust_id,
                "revenue_month": m,
                "billed_revenue": billed,
                "collected_revenue": collected,
            })

    return revenue_rows
