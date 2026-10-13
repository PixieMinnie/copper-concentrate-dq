import os
from sqlalchemy import create_engine


def get_engine():
    """SQLite by default; PostgreSQL if DATABASE_URL is set."""
    return create_engine(os.getenv("DATABASE_URL", "sqlite:///trade.db"))