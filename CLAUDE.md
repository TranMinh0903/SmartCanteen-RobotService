# Smart Canteen — robot-arm-service · Project Context (CLAUDE.md)

> File này để trợ lý AI (Claude Code) trong VS Code nắm nhanh dự án, tiến độ, và kế hoạch.
> Cập nhật lần cuối: **2026-06-15**.

## 1. Bối cảnh

- Đồ án **SU26SE019 — Smart Canteen System Using a Robotic Arm**, FPT University.
- Repo này = **`robot-arm-service`** (Python/FastAPI): điều khiển **3 cánh tay FAIRINO FR3**
  gắp đồ ăn phục vụ căng-tin. Gộp **điều khiển robot + AI vision** trong 1 process
  (KHÔNG cần C# gateway).
- Các mảnh anh em:
  - **Backend** .NET 8 + PostgreSQL — GitHub `TieHung23/SmartCanteen` (orders, wallet, sessions).
  - **Unity sim** (demo hội đồng) — `TranMinh0903/FAIRINO_FR3_FoodServing` (Built-in RP).
  - **Unity URP shell** — `TranMinh0903/SmartCanteen-RobotSimulation` (trống, để build sau).
- **Tài liệu triển khai đầy đủ (v3.0):** `D:\FPTStudy\Capstone\KE_HOACH_TRIEN_KHAI_ROBOT_ARM.docx`
  (§13 kiến trúc Arm, §14 luồng phục vụ; 4 sơ đồ). Đọc khi cần chi tiết.
- Tham khảo pattern: dự án cờ `D:\FPTStudy\Capstone\xiangqi_robot_TrainningAI_Final_6`
  (FAIRINO FR5, Python, SDK in-process, teaching points, YOLO, DRY_RUN).

## 2. Kiến trúc chốt — PUSH / BUFFER

- **Trigger = THANH TOÁN** (không phải quét QR). BE bind `ServingJob{Order↔Tray}` lúc trả tiền
  → **đẩy (SignalR)** cho service → robot **ráp sẵn** → khay xếp chờ trên **kệ pickup nhiều ô**.
  **QR pickup** của HS chỉ để **xác thực + lộ ô** khi tới lấy (lệch BR-135 gốc, đã chấp nhận).
- **Robot tìm vị trí** = **teaching point** (tô ở đầu lane kệ gravity, con lăn đùn ra; dạy 1 lần).
- **Nhận diện món** = **QUÉT QR CHÉN** (chống staff để nhầm lane); YOLO = lớp an toàn phụ.
- **3 tay = 3 IP riêng** (192.168.58.2/.3/.4) — đổi IP qua Web UI/Pendant (doc §13.3).
  1 service giữ **3 kết nối** (`Robot.RPC(ip)`) chạy song song.
- **SignalR outbound**: robot nối RA Backend (vượt NAT) — nhận job, báo trạng thái.
- **3 mã (đừng lẫn):** QR chén = đúng MÓN · mã khay (ArUco/barcode) = khay là ORDER nào ·
  QR pickup = HS xác thực.
- **DB:** 10 bảng (8 cốt lõi + `Tray` + `PickupSlot`); `ServingJob`+TrayId.

## 3. Trạng thái hiện tại (scaffold — chạy được DRY_RUN)

✅ **ĐÃ CÓ (khung + stub, test pass):**
- `app/main.py` — FastAPI (`/health` `/state` `/order`) + lifespan (fleet + job loop + SignalR).
- `app/orchestrator.py` — FIFO queue + **job loop vô hạn** + **pipeline dispatch** 3 trạm.
- `app/robot/fleet.py` — `RobotFleet` 3 kết nối, định tuyến theo station/category.
- `app/robot/fr3_robot.py` — `FR3Robot` bọc SDK; `pick_and_place` (teaching point); **DRY_RUN**.
- `app/vision/qr_scanner.py` — `verify_dish` (nhận diện món; stub trả True khi DRY_RUN).
- `app/vision/yolo_check.py` — lớp kiểm tra phụ (tùy chọn).
- `app/signalr/client.py` — nối RA BE, `on ReceiveJob` → submit; `ReportStatus`.
- `app/config.py` (.env), `app/schemas.py` (ServingJob/Item/StatusUpdate).
- `tests/test_dispatch.py` — **PASS** (pytest, DRY_RUN).
- Môi trường: **Python 3.12.10**, `.venv`, deps cài xong (**numpy<2** cho opencv 4.9).

🔲 **CHƯA LÀM (stub/TODO — cần code thật):**
- Tích hợp **SDK fairino thật** (đặt `robot_sdk_core.py` vào `app/robot/sdk/`, tắt DRY_RUN).
- **Motion thật** — trình tự gắp/đặt 3 độ cao an toàn (mở kẹp→SAFE_Z→PICK_Z→đóng→SAFE_Z→PLACE).
- **Teaching points** thật (LANE_Sx_<dish>, PLACE_Sx) — Manager dạy trên controller.
- **QR chén đọc camera thật** (`cv2.QRCodeDetector` / pyzbar) cho từng trạm.
- **SignalR nối Backend thật** (điền `BACKEND_HUB_URL`/token, khớp contract BE).
- **YOLO** train món Việt → `models/food_v1.pt` (lớp an toàn).
- Map **Tay↔Category** (Dish.CategoryId), đồng bộ **ShelfStock**, error/retry per-arm.

## 4. Cách chạy

```bash
.venv\Scripts\activate
pytest -q                              # test logic (DRY_RUN, không cần robot)
uvicorn app.main:app --reload          # chạy service
# test đẩy 1 đơn:
curl -X POST http://localhost:8000/order -H "Content-Type: application/json" ^
  -d "{\"orderId\":\"ORD-42\",\"tray\":5,\"items\":[{\"dish\":\"COM_TRANG\",\"station\":\"S1\"}]}"
```

## 5. Quy ước / Lưu ý

- **DRY_RUN=true** (trong `.env`) → chạy/test KHÔNG cần robot/AI thật.
- **KHÔNG commit:** `.env`, `app/robot/sdk/*.py`, `*.pt`, `models/` (đã `.gitignore`).
- **KHÔNG hardcode** IP/secret trong code → để `.env` (bài học từ dự án cờ lộ JWT).
- ⚠️ **KHÔNG thêm `Co-Authored-By: Claude`** vào commit (đồ án có hội đồng review).
  Tác giả commit = `TranMinh0903`.
- **numpy<2** (opencv 4.9 crash với numpy 2.x).
- Python ở `C:\Users\Gigabyte\AppData\Local\Programs\Python\Python312\python.exe`
  (PATH có thể chưa refresh — dùng `.venv` cho chắc).

## 6. Roadmap — việc tiếp theo (ưu tiên trên xuống)

1. **`app/robot/teaching_points.py`** + **`app/robot/motion.py`** — registry điểm dạy +
   trình tự gắp/đặt 3 độ cao an toàn (code thật, vẫn chạy được ở DRY_RUN).
2. **Tích hợp SDK fairino** — đặt SDK vào `app/robot/sdk/`, thử connect + MoveJ **1 tay** trước.
3. **QR chén thật** — `cv2.QRCodeDetector` đọc 1 trạm, verify đúng món.
4. **SignalR nối Backend thật** — khớp method `ReceiveJob`/`ReportStatus` với BE.
5. **Đóng gói pro** — `Dockerfile`, `pyproject.toml`, logging + retry, `docs/ARCHITECTURE.md`.
6. **YOLO món Việt** — train `food_v1.pt`, bật lớp kiểm tra an toàn.
7. **End-to-end** — BE đẩy đơn → service ráp (DRY_RUN robot) → báo done → BE cập nhật.
