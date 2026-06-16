"""Cấu hình service — đọc từ .env (KHÔNG hardcode IP/secret)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DRY_RUN: bool = True

    # 3 cánh tay — mỗi con 1 IP riêng
    ARM_S1_IP: str = "192.168.58.2"
    ARM_S2_IP: str = "192.168.58.3"
    ARM_S3_IP: str = "192.168.58.4"
    ARM_RPC_PORT: int = 20003

    ARM_S1_CATEGORY: str = "COM"
    ARM_S2_CATEGORY: str = "MAN"
    ARM_S3_CATEGORY: str = "CANH"

    BACKEND_HUB_URL: str = ""
    BACKEND_TOKEN: str = ""

    SERVICE_HOST: str = "0.0.0.0"
    SERVICE_PORT: int = 8000

    YOLO_MODEL_PATH: str = "models/food_v1.pt"
    QR_VERIFY_ENABLED: bool = True

    @property
    def arms(self) -> dict[str, dict]:
        """Map trạm → {ip, category}."""
        return {
            "S1": {"ip": self.ARM_S1_IP, "category": self.ARM_S1_CATEGORY},
            "S2": {"ip": self.ARM_S2_IP, "category": self.ARM_S2_CATEGORY},
            "S3": {"ip": self.ARM_S3_IP, "category": self.ARM_S3_CATEGORY},
        }


settings = Settings()
