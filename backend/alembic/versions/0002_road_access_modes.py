"""Store mode-specific road access information.

Revision ID: 0002_road_access_modes
Revises: 0001_initial_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_road_access_modes"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("road_edges", sa.Column("car_access", sa.String(length=80)))
    op.add_column("road_edges", sa.Column("bike_access", sa.String(length=80)))
    op.add_column("road_edges", sa.Column("foot_access", sa.String(length=80)))
    op.add_column("road_edges", sa.Column("bike_one_way", sa.Boolean()))


def downgrade() -> None:
    op.drop_column("road_edges", "bike_one_way")
    op.drop_column("road_edges", "foot_access")
    op.drop_column("road_edges", "bike_access")
    op.drop_column("road_edges", "car_access")
