from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Index, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RoadNode(Base):
    __tablename__ = "road_nodes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    location: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )


class RoadEdge(Base):
    __tablename__ = "road_edges"
    __table_args__ = (
        Index("ix_road_edges_source_node", "source_node"),
        Index("ix_road_edges_target_node", "target_node"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_node: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("road_nodes.id", ondelete="CASCADE"), nullable=False
    )
    target_node: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("road_nodes.id", ondelete="CASCADE"), nullable=False
    )
    distance_meters: Mapped[float] = mapped_column(Float, nullable=False)
    road_type: Mapped[str | None] = mapped_column(String(80))
    access_type: Mapped[str | None] = mapped_column(String(80))
    one_way: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
