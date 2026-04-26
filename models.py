from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    name = Column(String)
    role = Column(String, default="admin")  # superadmin, admin
    created_at = Column(DateTime, default=datetime.now)

    reports = relationship("Report", back_populates="user")


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # 담당 관리자
    name = Column(String)
    email = Column(String)
    company = Column(String)
    memo = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    reports = relationship("Report", back_populates="client")
    user = relationship("User", foreign_keys=[user_id])


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    report_type = Column(String)
    input_data = Column(Text)
    prompt_used = Column(Text)
    result = Column(Text)
    status = Column(String, default="draft")  # draft, submitted, approved, rejected
    reject_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    client = relationship("Client", back_populates="reports")
    user = relationship("User", back_populates="reports")
