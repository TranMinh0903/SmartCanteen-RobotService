"""DEMO: webcam đọc DOTCODE/QR trên nắp hộp → ĐẾM số lượng từng món ra từ bếp.

Dùng đúng module của service: app/vision/camera.py + app/vision/codes.py
(nên chạy được ở đây = chạy được trong service).

Chạy:  .venv\\Scripts\\python scan_dotcode.py            # cam = CAM_INTAKE_INDEX trong .env
       .venv\\Scripts\\python scan_dotcode.py 1          # chọn index khác

Trong cửa sổ:  q = thoát,  r = reset bộ đếm.
Mỗi mã (vd "CA_KHO") xuất hiện sẽ +1 vào bộ đếm; cùng 1 mã phải CÁCH NHAU >1s
mới tính hộp mới (debounce — hộp đứng yên không bị đếm trùng).
"""
import sys
import time
import cv2

from app.vision.camera import get_camera
from app.vision import codes

GAP = 1.0   # giây — cùng mã cách nhau > GAP mới tính là hộp mới


def main():
    index = None
    for a in sys.argv[1:]:
        if a.isdigit():
            index = int(a)
    cam = get_camera(index)
    if not cam.open():
        print("Không mở được camera. Chạy: python test_camera.py --list / --probe <idx>")
        return
    print(f"Đang đọc dotcode từ camera index {cam.index} (backend {cam.backend}). q=thoát, r=reset.")

    counts: dict[str, int] = {}
    last_seen: dict[str, float] = {}
    total = 0
    while True:
        frame = cam.grab()
        if frame is None:
            print("Mất khung -> dừng.")
            break
        now = time.time()
        for payload, pts in codes.detect(frame):
            p = pts.astype(int).reshape(-1, 2)
            cv2.polylines(frame, [p], True, (0, 220, 0), 2)
            cv2.putText(frame, payload, (p[0][0], max(20, p[0][1] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 0), 2)
            # đếm có debounce theo từng mã
            if now - last_seen.get(payload, -999) > GAP:
                counts[payload] = counts.get(payload, 0) + 1
                total += 1
                print(f"[+1] {payload}  (tổng {payload}={counts[payload]})")
            last_seen[payload] = now

        # overlay bảng đếm
        y = 26
        cv2.putText(frame, f"TONG: {total}", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 140, 255), 2)
        for name, c in sorted(counts.items()):
            y += 26
            cv2.putText(frame, f"{name}: {c}", (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("scan_dotcode", frame)
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        if k == ord('r'):
            counts.clear()
            last_seen.clear()
            total = 0
            print("-- reset bộ đếm --")

    cam.release()
    cv2.destroyAllWindows()
    print("\nKết quả đếm:", counts)


if __name__ == "__main__":
    main()
