import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CreditUnion(Base):
    __tablename__ = "credit_unions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    credit_union_id: Mapped[int] = mapped_column(
        ForeignKey("credit_unions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "credit_union_id", "name", name="uq_products_credit_union_id_name"
        ),
    )


class Ruleset(Base):
    """One full version of a credit union's rules for its whole product
    catalog. PUT inserts a new row and flips the previous is_latest row
    to false; existing rows are never updated or deleted.
    """

    __tablename__ = "rulesets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    credit_union_id: Mapped[int] = mapped_column(
        ForeignKey("credit_unions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    rules: Mapped[list] = mapped_column(JSONB, nullable=False)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "credit_union_id", "version", name="uq_rulesets_credit_union_id_version"
        ),
        Index(
            "uq_rulesets_one_latest_per_credit_union",
            "credit_union_id",
            unique=True,
            postgresql_where=text("is_latest"),
        ),
    )


class MemberProfile(Base):
    """One version of one member's profile. `id` uniquely identifies this
    version; `member_id` is stable across all versions of the same
    member and is not the primary key.

    Not implemented here: the evaluate engine will later decide, on
    ingest, whether an incoming profile matches the current is_latest
    row or requires inserting a new version.
    """

    __tablename__ = "member_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String, nullable=False)
    profile_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "member_id", "version", name="uq_member_profiles_member_id_version"
        ),
        Index(
            "uq_member_profiles_one_latest_per_member",
            "member_id",
            unique=True,
            postgresql_where=text("is_latest"),
        ),
    )


class Decision(Base):
    """Append-only audit ledger of eligibility decisions. Insert-only:
    no application role should be granted UPDATE/DELETE on this table.
    """

    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    credit_union_id: Mapped[int] = mapped_column(
        ForeignKey("credit_unions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    profile_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("member_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ruleset_version_id: Mapped[int] = mapped_column(
        ForeignKey("rulesets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    context: Mapped[str] = mapped_column(String, nullable=False)
    eligible_product_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    audit: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_decisions_credit_union_id_created_at", "credit_union_id", "created_at"),
    )
