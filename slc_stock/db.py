from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from slc_stock.config import DATABASE_URL
from slc_stock.models import Base

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return Session()
