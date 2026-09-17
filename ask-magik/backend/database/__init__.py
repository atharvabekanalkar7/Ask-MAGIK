"""
Database package for Ask MAGIK
Provides SQLAlchemy session management and ORM models.
"""

from .connection import engine, SessionLocal, get_db, Base
from .models import (
    SubscriberProfile,
    UsageDaily,
    CampaignResponse,
    RevenueMonthly,
    ChurnEvent,
)

__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "Base",
    "SubscriberProfile",
    "UsageDaily",
    "CampaignResponse",
    "RevenueMonthly",
    "ChurnEvent",
]
