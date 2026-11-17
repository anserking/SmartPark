"""Create the initial SmartPark schema.

Revision ID: 0001_initial_schema
Revises:
"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "destinations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("osm_id", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_destinations"),
        sa.UniqueConstraint("osm_id", name="uq_destinations_osm_id"),
    )
    op.create_index("ix_destinations_name", "destinations", ["name"], unique=False)
    op.create_index(
        "ix_destinations_location_gist",
        "destinations",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )

    op.create_table(
        "parking_spots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column(
            "location",
            Geography(geometry_type="GEOMETRY", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("osm_id", sa.String(length=80), nullable=True),
        sa.Column("source", sa.String(length=32), server_default="osm", nullable=False),
        sa.Column("parking_type", sa.String(length=80), nullable=True),
        sa.Column("hourly_fee", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("supports_car", sa.Boolean(), nullable=True),
        sa.Column("supports_bike", sa.Boolean(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("available_spaces", sa.Integer(), nullable=True),
        sa.Column(
            "availability_status",
            sa.String(length=16),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column(
            "verification_status",
            sa.String(length=16),
            server_default="unverified",
            nullable=False,
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "availability_status IN ('verified', 'unverified', 'unavailable', 'unknown')",
            name="availability_status",
        ),
        sa.CheckConstraint(
            "verification_status IN ('verified', 'unverified')",
            name="verification_status",
        ),
        sa.CheckConstraint(
            "capacity IS NULL OR capacity >= 0",
            name="capacity_nonnegative",
        ),
        sa.CheckConstraint(
            "available_spaces IS NULL OR available_spaces >= 0",
            name="available_spaces_nonnegative",
        ),
        sa.CheckConstraint(
            "hourly_fee IS NULL OR hourly_fee >= 0",
            name="hourly_fee_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_parking_spots"),
        sa.UniqueConstraint("osm_id", name="uq_parking_spots_osm_id"),
    )
    op.create_index(
        "ix_parking_spots_location_gist",
        "parking_spots",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )

    op.create_table(
        "road_nodes",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_road_nodes"),
    )

    op.create_table(
        "navigation_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("destination_id", sa.Uuid(), nullable=False),
        sa.Column("parking_id", sa.Uuid(), nullable=True),
        sa.Column("vehicle_type", sa.String(length=20), nullable=False),
        sa.Column("navigation_status", sa.String(length=32), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("parked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["destination_id"], ["destinations.id"], name="fk_navigation_sessions_destination_id_destinations"
        ),
        sa.ForeignKeyConstraint(
            ["parking_id"],
            ["parking_spots.id"],
            name="fk_navigation_sessions_parking_id_parking_spots",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_navigation_sessions"),
    )

    op.create_table(
        "road_edges",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_node", sa.BigInteger(), nullable=False),
        sa.Column("target_node", sa.BigInteger(), nullable=False),
        sa.Column("distance_meters", sa.Float(), nullable=False),
        sa.Column("road_type", sa.String(length=80), nullable=True),
        sa.Column("access_type", sa.String(length=80), nullable=True),
        sa.Column("one_way", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_node"],
            ["road_nodes.id"],
            name="fk_road_edges_source_node_road_nodes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_node"],
            ["road_nodes.id"],
            name="fk_road_edges_target_node_road_nodes",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_road_edges"),
    )
    op.create_index("ix_road_edges_source_node", "road_edges", ["source_node"], unique=False)
    op.create_index("ix_road_edges_target_node", "road_edges", ["target_node"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_road_edges_target_node", table_name="road_edges")
    op.drop_index("ix_road_edges_source_node", table_name="road_edges")
    op.drop_table("road_edges")
    op.drop_table("navigation_sessions")
    op.drop_table("road_nodes")
    op.drop_index("ix_parking_spots_location_gist", table_name="parking_spots")
    op.drop_table("parking_spots")
    op.drop_index("ix_destinations_location_gist", table_name="destinations")
    op.drop_index("ix_destinations_name", table_name="destinations")
    op.drop_table("destinations")
