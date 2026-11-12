"""Esquema inicial: catálogo CPC, versiones del dataset y conjunto de oro.

Revision ID: 0001
Revises:
Create Date: 2026-11-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cpc_code",
        sa.Column("code9", sa.String(9), primary_key=True),
        sa.Column("code5", sa.String(5), nullable=False),
        sa.Column("label", sa.String(300), nullable=False, server_default=""),
        sa.Column("n_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_year", sa.Integer(), nullable=False),
        sa.Column("last_year", sa.Integer(), nullable=False),
        sa.CheckConstraint("length(code9) = 9", name="ck_cpc_code_len9"),
        sa.CheckConstraint("code9 NOT GLOB '*[^0-9]*'", name="ck_cpc_code_digits"),
        sa.CheckConstraint("substr(code9, 1, 5) = code5", name="ck_cpc_code_parent"),
        sa.CheckConstraint("n_items >= 0", name="ck_cpc_code_items"),
    )
    op.create_index("ix_cpc_code_code5", "cpc_code", ["code5"])
    op.create_table(
        "dataset_version",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dataset_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("config_hash", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("train_rows", sa.Integer(), nullable=False),
        sa.Column("val_rows", sa.Integer(), nullable=False),
        sa.Column("test_rows", sa.Integer(), nullable=False),
        sa.Column("license", sa.String(40), nullable=False),
    )
    op.create_table(
        "gold_item",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_version_id", sa.Integer(), sa.ForeignKey("dataset_version.id"), nullable=False
        ),
        sa.Column("desc_norm", sa.String(300), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("original_code9", sa.String(9), nullable=False),
        sa.Column("gold_code9", sa.String(9), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("stratum", sa.String(40), nullable=False),
        sa.Column("reviewer", sa.String(40), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(500), nullable=False, server_default=""),
        sa.UniqueConstraint("dataset_version_id", "desc_norm", name="uq_gold_version_desc"),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'corrected', 'discarded')", name="ck_gold_status"
        ),
        sa.CheckConstraint(
            "(status IN ('pending', 'discarded')) OR "
            "(gold_code9 IS NOT NULL AND length(gold_code9) = 9)",
            name="ck_gold_code_when_reviewed",
        ),
    )


def downgrade() -> None:
    op.drop_table("gold_item")
    op.drop_table("dataset_version")
    op.drop_index("ix_cpc_code_code5", table_name="cpc_code")
    op.drop_table("cpc_code")
