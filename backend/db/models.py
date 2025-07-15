from sqlalchemy import Column, Integer, String, DateTime, Text, func, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.db.connection import Base

# === Prompt Logs ===

class PromptLog(Base):
    __tablename__ = "prompt_logs"

    id = Column(Integer, primary_key=True, index=True)                 # Unique ID
    prompt = Column(Text, nullable=False)                              # Raw prompt text
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Timestamp

    # New fields
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)   # Optional FK to User
    tag = Column(String(50), index=True, nullable=True)                # Optional label (e.g. 'feedback', 'code')
    tokens_used = Column(Integer, nullable=True)                       # Approx. token count (for analytics)
    source = Column(String(64), nullable=True)                         # API, CLI, Web, Agent, etc.

    # Relationship back to user
    user = relationship("User", back_populates="prompts")

    def __repr__(self):
        return f"<PromptLog id={self.id} user={self.user_id} tag={self.tag}>"

# === Users ===

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    api_key = Column(String(256), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # New fields
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    usage_count = Column(Integer, default=0)
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    # Reverse relationship to prompt logs
    prompts = relationship("PromptLog", back_populates="user")

    def __repr__(self):
        return f"<User id={self.id} username={self.username} active={self.is_active}>"
