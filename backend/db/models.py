from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    func,
    ForeignKey,
    Boolean,
    Index,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import relationship
from backend.db.connection import Base

# -----------------------------------------------------------------------------
# Mixins / Utilities
# -----------------------------------------------------------------------------

class ModelMixin:
    """
    Common helper mixin for ORM models.
    Provides lightweight serialization and convenience methods that do not
    change existing behavior of services using these models.
    """

    def as_dict(self) -> dict:
        """
        Serialize model columns into a plain dict (relationships excluded).
        Safe for logs/JSON responses.
        """
        data = {}
        for col in self.__table__.columns:  # type: ignore[attr-defined]
            data[col.name] = getattr(self, col.name)
        return data


# -----------------------------------------------------------------------------
# Prompt Logs
# -----------------------------------------------------------------------------

class PromptLog(ModelMixin, Base):
    __tablename__ = "prompt_logs"

    id = Column(Integer, primary_key=True, index=True)  # Unique ID
    prompt = Column(Text, nullable=False)               # Raw prompt text
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # Timestamp

    # New fields (kept compatible with existing code)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional FK to User
    tag = Column(String(50), index=True, nullable=True)               # Optional label (e.g. 'feedback', 'code')
    tokens_used = Column(Integer, nullable=True)                      # Approx. token count (for analytics)
    source = Column(String(64), nullable=True)                        # API, CLI, Web, Agent, etc.

    # Relationship back to user
    user = relationship("User", back_populates="prompts")

    # Helpful composite indexes for common analytics queries
    __table_args__ = (
        Index("ix_prompt_logs_created_at_desc", created_at.desc()),
        Index("ix_prompt_logs_user_tag_time", user_id, tag, created_at.desc()),
    )

    def short_preview(self, length: int = 120) -> str:
        """
        Return a short, safe preview of the prompt (for UI lists / logs).
        """
        if not self.prompt:
            return ""
        return (self.prompt[:length] + "…") if len(self.prompt) > length else self.prompt

    def __repr__(self):
        return f"<PromptLog id={self.id} user={self.user_id} tag={self.tag}>"


# -----------------------------------------------------------------------------
# Users
# -----------------------------------------------------------------------------

class User(ModelMixin, Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    api_key = Column(String(256), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # New fields (backward compatible)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    usage_count = Column(Integer, default=0)
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    # Reverse relationship to prompt logs
    prompts = relationship("PromptLog", back_populates="user")

    # Optional unique constraint to guard future username/API key invariants
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("api_key", name="uq_users_api_key"),
        Index("ix_users_active_last_accessed", is_active, last_accessed.desc()),
    )

    # ---------------- Convenience methods (non-breaking) ----------------

    def touch_access(self, ts_func=func.now()):
        """
        Update last_accessed and increment usage counter.
        Safe to call from services when a user hits the API.
        """
        self.last_accessed = ts_func  # SQL-side timestamp for consistency
        self.usage_count = (self.usage_count or 0) + 1

    def deactivate(self):
        """
        Soft-deactivate the user account (does not delete any data).
        """
        self.is_active = False
        self.is_deleted = True

    def reactivate(self):
        """
        Reactivate a previously deactivated user.
        """
        self.is_active = True
        self.is_deleted = False

    def __repr__(self):
        return f"<User id={self.id} username={self.username} active={self.is_active}>"


# -----------------------------------------------------------------------------
# System Settings (optional, non-breaking new table)
# -----------------------------------------------------------------------------

class SystemSetting(ModelMixin, Base):
    """
    NEW: Small key/value store for runtime-configurable flags.
    This is optional and does not affect existing flows.
    """
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(128), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<SystemSetting key={self.key}>"


# -----------------------------------------------------------------------------
# Events / Hooks
# -----------------------------------------------------------------------------

@event.listens_for(PromptLog, "after_insert")
def _promptlog_after_insert(mapper, connection, target: PromptLog):
    """
    NEW: Lightweight analytics hook.
    When a PromptLog is inserted with a user_id, bump that user's usage_count
    and update last_accessed. Uses a direct connection execute to avoid
    requiring a session here and to keep this hook side-effect minimal.
    """
    try:
        if target.user_id:
            connection.execute(
                # SQLAlchemy Core update to avoid importing the mapped User table here
                User.__table__.update()  # type: ignore[attr-defined]
                .where(User.id == target.user_id)
                .values(
                    usage_count=User.usage_count + 1,  # type: ignore[operator]
                    last_accessed=func.now(),
                )
            )
    except Exception:
        # Never raise from ORM event listeners; keep it silent to avoid breaking the write.
        # Analytics can be recomputed later if needed.
        pass
