# Smart Canteen — robot-arm-service

Service Python điều khiển **3 cánh tay FAIRINO FR3** phục vụ đồ ăn trong căng-tin
thông minh (SU26SE019). Gộp **điều khiển robot + AI vision** vào 1 process duy nhất
(không cần C# gateway). Tham khảo pattern: `xiangqi_robot_TrainningAI_Final_6`.

> Kiến trúc & luồng chi tiết: `D:\FPTStudy\Capstone\KE_HOACH_TRIEN_KHAI_ROBOT_ARM.docx` (v3.0, §13–§14).

## Mô hình (bản chốt v3.0 — PUSH / BUFFER)

```
Thanh toán → BE bind ServingJob{Order↔Tray} → ──SignalR──► service (PUSH)
   → orchestrator: FIFO queue + job loop → thả khay vào line
   → RobotFleet: mỗi trạm gắp (teaching point) + QUÉT QR CHÉN verify đúng món
   → khay đủ món → đẩy ra Staff → service ──SignalR──► BE "DONE"
```

- **Robot tìm vị trí** = teaching point (tô ở đầu lane kệ gravity, dạy 1 lần).
- **Nhận diện món** = QUÉT QR CHÉN (chống staff để nhầm lane); YOLO = lớp an toàn phụ.
- **3 tay = 3 IP riêng** (192.168.58.2/.3/.4), 1 service giữ 3 kết nối song song.
- **Trigger = thanh toán** (push); QR pickup chỉ để HS xác thực + lộ ô khi lấy.

## Cấu trúc

```
robot-arm-service/
├── app/
│   ├── main.py            # FastAPI: /health /order(test) /state + khởi động fleet + SignalR
│   ├── orchestrator.py    # FIFO queue + job loop + dispatch pipeline 3 trạm
│   ├── config.py          # IP robot, port, teaching points, ngưỡng (đọc .env)
│   ├── schemas.py         # DTO khớp Backend (ServingJob, Item, StatusUpdate)
│   ├── robot/
│   │   ├── fleet.py        # RobotFleet — 3 kết nối {S1,S2,S3}
│   │   ├── fr3_robot.py    # điều khiển 1 FR3 (bọc fairino SDK) + DRY_RUN
│   │   └── sdk/            # đặt fairino SDK (robot_sdk_core.py) vào đây — KHÔNG commit
│   ├── vision/
│   │   ├── qr_scanner.py   # quét QR chén = nhận diện món (chính)
│   │   └── yolo_check.py   # YOLO kiểm tra (tuỳ chọn, an toàn)
│   └── signalr/
│       └── client.py       # SignalR client nối RA Backend (nhận job, báo done)
├── tests/test_dispatch.py  # test logic dispatch ở chế độ DRY_RUN
├── .env.example · requirements.txt · RUN.bat
```

## Chạy

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # sửa IP/port/BE URL
# DRY_RUN=true để test KHÔNG cần robot thật
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Test nhanh (không cần robot, DRY_RUN):
```bash
pytest -q
curl -X POST http://localhost:8000/order -H "Content-Type: application/json" -d "{\"orderId\":\"ORD-42\",\"tray\":5,\"items\":[{\"dish\":\"COM_TRANG\",\"station\":\"S1\"}]}"
```

## ⚠️ Bảo mật
- KHÔNG commit `fairino SDK`, `.env`, token, model `.pt`. Xem `.gitignore`.
- IP robot / BE URL / secret → để trong `.env` (đừng hardcode — bài học từ dự án cờ).
