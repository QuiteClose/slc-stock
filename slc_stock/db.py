import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from slc_stock.config import DATABASE_URL
from slc_stock.models import Base

log = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)


def _migrate_db():
    """Add columns that were introduced after the initial schema."""
    insp = inspect(engine)
    if "quotes" not in insp.get_table_names():
        return
    columns = {col["name"] for col in insp.get_columns("quotes")}
    with engine.begin() as conn:
        if "adjusted" not in columns:
            log.info("Migrating: adding 'adjusted' column to quotes table")
            conn.execute(
                text("ALTER TABLE quotes ADD COLUMN adjusted BOOLEAN DEFAULT 1")
            )


def init_db():
    Base.metadata.create_all(engine)
    _migrate_db()


def get_session():
    return Session()
