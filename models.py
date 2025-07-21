# models.py
from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_pro = Column(Boolean, default=False)
    registered_date = Column(DateTime, default=datetime.utcnow)

    # This creates a relationship so you can easily access
    # all processed files for a user. e.g., my_user.processed_files
    processed_files = relationship("Usage", back_populates="owner")

class Usage(Base):
    __tablename__ = "usage_tracking"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String)
    processed_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)

    owner = relationship("User", back_populates="processed_files")