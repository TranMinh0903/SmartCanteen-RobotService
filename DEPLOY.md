# Deploy Edge (MOCK) lên server

Edge chạy trên server ở chế độ **DRY_RUN=true** (giả lập robot): pull đơn → chạy trọn vòng đời
ServingJob → báo status/heartbeat về BE. Mục đích: **integration test 24/7 + FE có data thật**,
không cần laptop Minh / robot vật lý.

> Cùng codebase với Edge thật. Khác nhau DUY NHẤT ở `.env`:
> server `DRY_RUN=true` (mock) — laptop Minh `DRY_RUN=false` (điều khiển FR3 thật).

## ⚠️ QUY TẮC SỐNG CÒN

**Khi demo ROBOT THẬT (Edge chạy từ laptop Minh) → PHẢI TẮT Edge trên server trước:**

```bash
docker compose stop robot-edge      # demo xong:  docker compose start robot-edge
```

Không tắt thì 2 Edge **giành đơn nhau**: con mock trên server chộp job và "hoàn thành giả"
trong tích tắc — robot thật không bao giờ tới lượt gắp.

## Bước 1 — Tạo tài khoản robot trên DB SERVER (làm 1 lần)

Edge đăng nhập BE bằng JWT như client thường (`RobotHub` chỉ cần `[Authorize]`, không cần role).
Tạo 1 tài khoản riêng (vd `robot-service@smartcanteen.local`) qua luồng đăng ký bình thường
hoặc insert thẳng DB — để `CreatedBy`/audit trong RobotEventLogs có danh tính rõ ràng.

Login lấy token:

```bash
curl -s -X POST http://178.128.100.1:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"<email robot account>","password":"<password>"}'
# copy accessToken trong response
```

> Token có hạn dùng. Nếu sau này log Edge báo 401 → login lại lấy token mới, sửa `.env`,
> `docker compose restart robot-edge`. (Backlog: cơ chế tự refresh.)

## Bước 2 — Clone + tạo `.env`

```bash
git clone https://github.com/TranMinh0903/SmartCanteen-RobotService.git
cd SmartCanteen-RobotService
```

Tạo file `.env`:

```env
# ===== Edge MOCK trên server =====
DRY_RUN=true
FIRST_TEST_DEMO_MOVE=false        # false = đi luồng thật (log đủ Received/PickCompleted từng món/PlaceCompleted)
QR_VERIFY_ENABLED=false           # không có camera trên server

BACKEND_HUB_URL=http://178.128.100.1:8080/hubs/robot
BACKEND_TOKEN=<accessToken lấy ở Bước 1>

SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
```

(IP robot `ARM_S*_IP` giữ mặc định — DRY_RUN không kết nối tới chúng.)

## Bước 3 — Build + chạy

```bash
docker compose up -d --build
docker logs -f robot-edge     # phải thấy: "DRY_RUN=True", "SignalR ... on_open", "job loop bắt đầu"
```

## Bước 4 — Verify (5 phút)

1. `curl http://localhost:8000/health` → `{"ok": true, "dry_run": true}`
2. Swagger BE → `GET /api/manager/robot-arms`: sau ~25s các arm đã đăng ký (Code S1/S2/S3)
   chuyển `Offline → Idle` (heartbeat 20s/lần).
3. Đặt 1 đơn test trên FE/Swagger → xem `RobotEventLogs`: JobReceived → PickCompleted (từng món,
   có `DishId`) → PlaceCompleted; ServingJob kết ở `OnShelf`... theo luồng.
4. Nếu job không chạy: check `docker logs robot-edge` — hay gặp nhất là token sai/401
   (tài khoản không tồn tại trên DB server) hoặc `BACKEND_HUB_URL` sai.

## Ghi chú vận hành

- **Đổi `.env` = phải `docker compose restart robot-edge`** (env chỉ đọc lúc khởi động).
- Container tự chạy lại khi server reboot (`restart: unless-stopped`).
- Cập nhật code mới: `git pull && docker compose up -d --build`.
- Edge trên server **không cần**: SDK fairino (gitignored), camera, teaching_points đúng chuẩn —
  DRY_RUN bỏ qua toàn bộ phần vật lý.
