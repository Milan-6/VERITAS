import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base
from app.core.encryption import encrypt_secret, decrypt_secret


class IntegrationCredential(Base):
    __tablename__ = "integration_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # "zotero", "mendeley"
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    external_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # e.g., Zotero library/user ID
    settings_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="integration_credentials")
    workspace = relationship("Workspace", backref="integration_credentials")

    __table_args__ = (
        Index("ix_integration_user_provider", "user_id", "provider"),
        Index("ix_integration_workspace_provider", "workspace_id", "provider"),
    )

    def set_api_key(self, plain_key: str):
        self.encrypted_api_key = encrypt_secret(plain_key)

    def get_api_key(self) -> str:
        return decrypt_secret(self.encrypted_api_key)


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    events_subscribed: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # e.g., ["document.ingested", ...]
    secret_key: Mapped[str] = mapped_column(String(255), nullable=False)  # HMAC signing secret
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workspace = relationship("Workspace", backref="webhook_subscriptions")
    user = relationship("User", backref="webhook_subscriptions")

    __table_args__ = (
        Index("ix_webhook_workspace_active", "workspace_id", "is_active"),
    )
