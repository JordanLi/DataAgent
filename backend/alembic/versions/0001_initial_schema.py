"""initial schema

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── datasources ──────────────────────────────────────────────────────────
    op.create_table(
        "datasources",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "name", sa.String(128), nullable=False, unique=True
        ),
        sa.Column(
            "db_type",
            sa.Enum("mysql", name="db_type_enum"),
            nullable=False,
            server_default="mysql",
        ),
        sa.Column("host", sa.String(256), nullable=False),
        sa.Column("port", sa.Integer, nullable=False, server_default="3306"),
        sa.Column("database", sa.String(128), nullable=False),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("encrypted_password", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── table_metadata ────────────────────────────────────────────────────────
    op.create_table(
        "table_metadata",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "datasource_id",
            sa.Integer,
            sa.ForeignKey("datasources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("table_name", sa.String(256), nullable=False),
        sa.Column("table_comment", sa.Text, nullable=True),
        sa.Column("columns_json", sa.Text, nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_table_metadata_datasource_id", "table_metadata", ["datasource_id"])

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(128), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "analyst", "viewer", name="user_role_enum"),
            nullable=False,
            server_default="analyst",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_username", "users", ["username"])

    # ── conversations ─────────────────────────────────────────────────────────
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    # ── messages ──────────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "conversation_id",
            sa.Integer,
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", name="message_role_enum"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("sql_generated", sa.Text, nullable=True),
        sa.Column("execution_time_ms", sa.Integer, nullable=True),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

    # ── business_terms ────────────────────────────────────────────────────────
    op.create_table(
        "business_terms",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "datasource_id",
            sa.Integer,
            sa.ForeignKey("datasources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("term_name", sa.String(128), nullable=False),
        sa.Column("definition", sa.Text, nullable=True),
        sa.Column("sql_expression", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("datasource_id", "term_name", name="uq_term_per_datasource"),
    )
    op.create_index("ix_business_terms_datasource_id", "business_terms", ["datasource_id"])

    # ── field_aliases ─────────────────────────────────────────────────────────
    op.create_table(
        "field_aliases",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "datasource_id",
            sa.Integer,
            sa.ForeignKey("datasources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("table_name", sa.String(256), nullable=False),
        sa.Column("column_name", sa.String(256), nullable=False),
        sa.Column("alias_name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "datasource_id", "table_name", "column_name", name="uq_alias_per_column"
        ),
    )
    op.create_index("ix_field_aliases_datasource_id", "field_aliases", ["datasource_id"])

    # ── enum_mappings ─────────────────────────────────────────────────────────
    op.create_table(
        "enum_mappings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "datasource_id",
            sa.Integer,
            sa.ForeignKey("datasources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("table_name", sa.String(256), nullable=False),
        sa.Column("column_name", sa.String(256), nullable=False),
        sa.Column("enum_value", sa.String(256), nullable=False),
        sa.Column("display_label", sa.String(256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "datasource_id",
            "table_name",
            "column_name",
            "enum_value",
            name="uq_enum_value_per_column",
        ),
    )
    op.create_index("ix_enum_mappings_datasource_id", "enum_mappings", ["datasource_id"])

    # ── table_relations ───────────────────────────────────────────────────────
    op.create_table(
        "table_relations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "datasource_id",
            sa.Integer,
            sa.ForeignKey("datasources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_table", sa.String(256), nullable=False),
        sa.Column("source_column", sa.String(256), nullable=False),
        sa.Column("target_table", sa.String(256), nullable=False),
        sa.Column("target_column", sa.String(256), nullable=False),
        sa.Column(
            "relation_type",
            sa.Enum(
                "one_to_one",
                "one_to_many",
                "many_to_one",
                "many_to_many",
                name="relation_type_enum",
            ),
            nullable=False,
            server_default="many_to_one",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_table_relations_datasource_id", "table_relations", ["datasource_id"])

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("datasource_id", sa.Integer, nullable=True),
        sa.Column("sql_executed", sa.Text, nullable=True),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_datasource_id", "audit_logs", ["datasource_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("table_relations")
    op.drop_table("enum_mappings")
    op.drop_table("field_aliases")
    op.drop_table("business_terms")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("users")
    op.drop_table("table_metadata")
    op.drop_table("datasources")

    op.execute("DROP TYPE IF EXISTS relation_type_enum")
    op.execute("DROP TYPE IF EXISTS message_role_enum")
    op.execute("DROP TYPE IF EXISTS user_role_enum")
    op.execute("DROP TYPE IF EXISTS db_type_enum")
