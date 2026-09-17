"""
SQLAlchemy ORM Models for Skyline Telecom DataMart
Ask MAGIK - Phase 1 Foundation

Tables:
1. subscriber_profile: Customer demographic, plan, segment, and lifecycle status.
2. usage_daily: Daily consumption of voice, data, and SMS per subscriber.
3. campaign_response: Marketing campaign impressions, offers, and customer responses.
4. revenue_monthly: Billed and collected financial metrics by month.
5. churn_events: Specific attrition events with reasons and channels.
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Date,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from backend.database.connection import Base


class SubscriberProfile(Base):
    """
    Core customer dimension table.
    Granularity: One record per subscriber.
    PII Policy: No names, phone numbers, or addresses are stored.
    """
    __tablename__ = "subscriber_profile"

    customer_id = Column(String(32), primary_key=True, index=True, nullable=False)
    plan = Column(String(64), nullable=False, index=True)
    region = Column(String(32), nullable=False, index=True)
    tenure_months = Column(Integer, nullable=False)
    segment = Column(String(32), nullable=False, index=True)
    customer_type = Column(String(32), nullable=False, index=True)
    activation_date = Column(Date, nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)  # 'Active' or 'Churned'

    # Relationships
    usage_records = relationship("UsageDaily", back_populates="subscriber", cascade="all, delete-orphan")
    campaign_records = relationship("CampaignResponse", back_populates="subscriber", cascade="all, delete-orphan")
    revenue_records = relationship("RevenueMonthly", back_populates="subscriber", cascade="all, delete-orphan")
    churn_records = relationship("ChurnEvent", back_populates="subscriber", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<SubscriberProfile(customer_id='{self.customer_id}', plan='{self.plan}', status='{self.status}')>"


class UsageDaily(Base):
    """
    Daily usage metrics table.
    Granularity: One row per customer per day.
    """
    __tablename__ = "usage_daily"

    usage_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(32), ForeignKey("subscriber_profile.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    usage_date = Column(Date, nullable=False, index=True)
    voice_minutes = Column(Float, nullable=False, default=0.0)
    data_mb = Column(Float, nullable=False, default=0.0)
    sms_count = Column(Integer, nullable=False, default=0)

    # Relationship
    subscriber = relationship("SubscriberProfile", back_populates="usage_records")

    __table_args__ = (
        Index("idx_usage_customer_date", "customer_id", "usage_date"),
    )

    def __repr__(self) -> str:
        return f"<UsageDaily(id={self.usage_id}, customer_id='{self.customer_id}', date='{self.usage_date}')>"


class CampaignResponse(Base):
    """
    Marketing campaign exposures and customer responses.
    Granularity: One row per campaign impression/contact.
    """
    __tablename__ = "campaign_response"

    campaign_response_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(32), ForeignKey("subscriber_profile.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_name = Column(String(128), nullable=False, index=True)
    campaign_date = Column(Date, nullable=False, index=True)
    campaign_type = Column(String(64), nullable=False, index=True)
    response = Column(String(32), nullable=False, index=True)  # 'Responded', 'Not Responded'
    offer_value = Column(Float, nullable=False, default=0.0)

    # Relationship
    subscriber = relationship("SubscriberProfile", back_populates="campaign_records")

    def __repr__(self) -> str:
        return f"<CampaignResponse(id={self.campaign_response_id}, campaign='{self.campaign_name}', response='{self.response}')>"


class RevenueMonthly(Base):
    """
    Monthly customer financial accounting.
    Granularity: One row per customer per billing month.
    """
    __tablename__ = "revenue_monthly"

    revenue_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(32), ForeignKey("subscriber_profile.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    revenue_month = Column(String(7), nullable=False, index=True)  # Format 'YYYY-MM'
    billed_revenue = Column(Float, nullable=False, default=0.0)
    collected_revenue = Column(Float, nullable=False, default=0.0)

    # Relationship
    subscriber = relationship("SubscriberProfile", back_populates="revenue_records")

    __table_args__ = (
        Index("idx_revenue_customer_month", "customer_id", "revenue_month"),
    )

    def __repr__(self) -> str:
        return f"<RevenueMonthly(id={self.revenue_id}, customer_id='{self.customer_id}', month='{self.revenue_month}', billed={self.billed_revenue})>"


class ChurnEvent(Base):
    """
    Customer attrition and cancellation events.
    Granularity: One row per churn event.
    """
    __tablename__ = "churn_events"

    churn_event_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(32), ForeignKey("subscriber_profile.customer_id", ondelete="CASCADE"), nullable=False, index=True)
    churn_date = Column(Date, nullable=False, index=True)
    churn_reason = Column(String(64), nullable=False, index=True)
    churn_channel = Column(String(64), nullable=False, index=True)

    # Relationship
    subscriber = relationship("SubscriberProfile", back_populates="churn_records")

    def __repr__(self) -> str:
        return f"<ChurnEvent(id={self.churn_event_id}, customer_id='{self.customer_id}', date='{self.churn_date}', reason='{self.churn_reason}')>"
