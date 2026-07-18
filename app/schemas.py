"""DTO khớp HỢP ĐỒNG BE (SignalR JSON, camelCase).

BE đẩy `ServingJobMessage` qua event "ReceiveJob"; service báo ngược
`ServingStatusUpdate` qua hub method "ReportStatus".
Field name = camelCase ĐÚNG như BE serialize (ASP.NET Core SignalR mặc định camelCase).
"""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, ConfigDict


class Item(BaseModel):
    """1 món trong job (BE: ServingJobItemMessage). BE hiện chỉ set dishId + quantity."""
    model_config = ConfigDict(extra="ignore")
    dishId: str | None = None
    dishName: str | None = None
    quantity: int = 1
    station: str | None = None        # BE có thể chưa set → route mặc định S1 khi test
    laneCode: str | None = None       # nhãn lane BE gửi (vd "S1-L2") → teaching point ưu tiên
    placeCode: str | None = None      # nhãn vị trí đặt trên khay (vd "PLACE_S1_2") → ưu tiên hơn index
    done: bool = False                # BE báo món ĐÃ phục vụ lượt trước (resume) → SKIP, khỏi gắp lại

    @property
    def dish(self) -> str:            # tiện log
        return self.dishName or self.dishId or "?"


class ServingJob(BaseModel):
    """BE -> service (event "ReceiveJob") = ServingJobMessage."""
    model_config = ConfigDict(extra="ignore")
    jobId: str | None = None
    orderId: str
    trayId: str | None = None
    trayCode: str | None = None
    items: list[Item] = []


class JobState(str, Enum):
    # vocab PHẢI khớp MapEventType của BE (không khớp -> BE fallback JobReceived, sai EventType):
    # received / pickstarted / pickcompleted / placecompleted / failed (so sánh không phân biệt hoa thường)
    DISPATCHED = "Received"          # nhận việc (BE: JobReceived)
    PICK_STARTED = "PickStarted"
    PICK_COMPLETED = "PickCompleted"
    PLACE_COMPLETED = "PlaceCompleted"
    DONE = "PlaceCompleted"          # job xong = đặt món xong (alias của PLACE_COMPLETED)
    FAILED = "Failed"


class StatusUpdate(BaseModel):
    """service -> BE (hub "ReportStatus") = ServingStatusUpdate."""
    model_config = ConfigDict(extra="ignore")
    orderId: str
    trayId: str | None = None
    state: str
    station: str | None = None
    dishId: str | None = None        # món của event mức món (PickCompleted/Error) -> BE ghi RobotEventLog.DishId
    message: str | None = None
