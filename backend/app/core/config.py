from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartPark API"
    environment: str = "development"
    database_url: str
    cors_origins: list[str] = ["http://localhost:5173"]
    admin_api_key: SecretStr | None = None
    google_maps_api_key: SecretStr | None = None
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    photon_url: str = "https://photon.komoot.io/api/"
    openrouteservice_api_key: SecretStr | None = None
    openrouteservice_directions_url: str = (
        "https://api.openrouteservice.org/v2/directions"
    )
    provider_timeout_seconds: float = Field(default=25, gt=0)
    road_network_timeout_seconds: int = Field(default=60, gt=0)
    geodata_cache_ttl_seconds: int = Field(default=21600, gt=0)
    provider_user_agent: str = (
        "SmartPark/1.0 (https://github.com/anserking/SmartPark)"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
