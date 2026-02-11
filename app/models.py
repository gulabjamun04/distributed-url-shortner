from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.db import Base

class URL(Base):
    __tablename__ = "urls"

    short_code = Column(String, primary_key=True, index=True)
    long_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<URL(short_code='{self.short_code}', long_url='{self.long_url}')>"
