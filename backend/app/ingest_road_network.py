import asyncio

from app.db.session import SessionLocal
from app.services.road_network_ingestion import (
    fetch_karachi_road_network,
    replace_road_network,
)


async def main() -> None:
    network = await fetch_karachi_road_network()
    with SessionLocal() as db:
        replace_road_network(db, network)
    print(
        f"Replaced Karachi road network with "
        f"{len(network.nodes)} nodes and {len(network.edges)} directed edges."
    )


if __name__ == "__main__":
    asyncio.run(main())
