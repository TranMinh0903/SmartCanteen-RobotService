# fairino SDK — đặt tay vào đây (KHÔNG commit)

Service cần **fairino Python SDK** (file `robot_sdk_core.py` — bản ~498KB trong dự án cờ
`xiangqi_robot_TrainningAI_Final_6/src/hardware/robot_sdk_core.py`, hoặc tải từ FAIRINO).

## Cách đặt
1. Copy `robot_sdk_core.py` (và file SDK đi kèm nếu có) vào thư mục này.
2. `app/robot/fr3_robot.py` import: `from app.robot.sdk.robot_sdk_core import Robot`.

## ⚠️ KHÔNG commit SDK lên Git
`.gitignore` đã chặn `app/robot/sdk/*.py` (trừ `__init__.py`). SDK là của FAIRINO — giữ local.

## DRY_RUN
Khi `DRY_RUN=true`, service KHÔNG import SDK → chạy/test logic được mà chưa cần SDK.
