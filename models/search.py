from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
from sqlalchemy.sql import func
from config.database import Base  # Import Base from your project


class SearchHistory(Base):
    __tablename__ = 'search_history'

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(50), nullable=False)
    search_query = Column(String(255), nullable=False)
    wikipedia_data = Column(JSON, nullable=True)
    result = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_agent = Column(String(255), nullable=True)
    region = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<SearchHistory(id={self.id}, ip_address={self.ip_address}, search_query={self.search_query}, timestamp={self.timestamp})>"

