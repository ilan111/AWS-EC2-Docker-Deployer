from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class RequestStatus(Base):
    __tablename__ = "requests_status"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), nullable=False)
    result = Column(Text)