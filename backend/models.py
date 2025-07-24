from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    """
    Represents a user in the database.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    plan = Column(String(50), nullable=False, default="free")
    stripe_customer_id = Column(String, unique=True, nullable=True)

    # This creates the one-to-many relationship.
    # A user can have many processed files.
    processed_files = relationship("ProcessedFile", back_populates="owner")


class ProcessedFile(Base):
    """
    Represents a document processed by a user, effectively tracking usage.
    """
    __tablename__ = "processed_files"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, index=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"))
    ip_address = Column(String)

    # This links a processed file back to its owner (a user).
    owner = relationship("User", back_populates="processed_files")