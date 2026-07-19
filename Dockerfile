# robot-arm-service — Edge cho Smart Canteen.
# Trên SERVER chạy DRY_RUN=true (mock, không cần robot/camera/SDK fairino).
# SDK fairino (app/robot/sdk/) gitignored — DRY_RUN không import nên không cần trong image.
FROM python:3.12-slim

# System libs cho opencv + pylibdmtx (chỉ dùng khi bật QR verify; cài sẵn cho đủ bộ)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libdmtx0b \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/robot-arm-service

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# KHÔNG --reload trong container (reload là đồ dev local)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
