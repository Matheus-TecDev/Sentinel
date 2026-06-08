"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-08 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "OPERATOR", "VIEWER", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "environment",
            sa.Enum("dev", "staging", "production", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("healthcheck_url", sa.String(length=2048), nullable=False),
        sa.Column("owner", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_services_environment"), "services", ["environment"], unique=False)
    op.create_index(op.f("ix_services_id"), "services", ["id"], unique=False)
    op.create_index(op.f("ix_services_name"), "services", ["name"], unique=False)

    op.create_table(
        "health_check_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("online", "offline", "degraded", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("http_status_code", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_health_check_results_checked_at"), "health_check_results", ["checked_at"], unique=False)
    op.create_index(op.f("ix_health_check_results_id"), "health_check_results", ["id"], unique=False)
    op.create_index(op.f("ix_health_check_results_service_id"), "health_check_results", ["service_id"], unique=False)
    op.create_index(op.f("ix_health_check_results_status"), "health_check_results", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_health_check_results_status"), table_name="health_check_results")
    op.drop_index(op.f("ix_health_check_results_service_id"), table_name="health_check_results")
    op.drop_index(op.f("ix_health_check_results_id"), table_name="health_check_results")
    op.drop_index(op.f("ix_health_check_results_checked_at"), table_name="health_check_results")
    op.drop_table("health_check_results")
    op.drop_index(op.f("ix_services_name"), table_name="services")
    op.drop_index(op.f("ix_services_id"), table_name="services")
    op.drop_index(op.f("ix_services_environment"), table_name="services")
    op.drop_table("services")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
