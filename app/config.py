"""Cấu hình service — đọc từ .env (KHÔNG hardcode IP/secret)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DRY_RUN: bool = True

    # TEST ĐẦU: nhận ReceiveJob -> chỉ làm 1 cú MOVE AN TOÀN trên S1 (xoay cổ tay),
    # BỎ QUA pick_and_place (chưa cần teaching point/gripper). Tắt khi vào luồng thật.
    FIRST_TEST_DEMO_MOVE: bool = True
    DEMO_STATION: str = "S1"

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

    # --- Camera (webcam HIKVISION đọc dotcode/QR nắp hộp) ---
    CAM_BACKEND: str = "msmf"      # msmf (HIKVISION 720p OK) | dshow | any
    CAM_INTAKE_INDEX: int = 1      # webcam top-down đọc nắp hộp (chạy test_camera.py --list để biết index)
    CAM_WIDTH: int = 1280
    CAM_HEIGHT: int = 720

    # Loại mã trên nắp hộp: qr | datamatrix | both (đọc cả hai).
    # Data Matrix cần pylibdmtx (+ setuptools<74 trên Python 3.12).
    CODE_KIND: str = "both"
    CODE_DM_TIMEOUT_MS: int = 150   # giới hạn thời gian decode Data Matrix mỗi khung (tránh tụt FPS)

    @property
    def arms(self) -> dict[str, dict]:
        """Map trạm → {ip, category}."""
        return {
            "S1": {"ip": self.ARM_S1_IP, "category": self.ARM_S1_CATEGORY},
            "S2": {"ip": self.ARM_S2_IP, "category": self.ARM_S2_CATEGORY},
            "S3": {"ip": self.ARM_S3_IP, "category": self.ARM_S3_CATEGORY},
        }


settings = Settings()
