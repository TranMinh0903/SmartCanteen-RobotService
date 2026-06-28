"""Test gắp/đặt THẬT bằng teaching point (chưa có gripper → chỉ chuyển động).

⚠️ THOÁT teach_record.py TRƯỚC (1 robot = 1 kết nối).
⚠️ Tay gần E-stop, vùng trống.

Chạy:  .venv\\Scripts\\python test_pick_real.py
"""
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

sys.path.insert(0, os.path.dirname(__file__))
from app.config import settings          # noqa: E402
from app.robot.fleet import fleet        # noqa: E402
from app.robot.teaching import load_points  # noqa: E402

# Trình tự an toàn (7 điểm bạn đã teach): tiếp cận cao -> giữa -> thấp khi gắp/đặt,
# rồi rút ngược ra trước khi sang chỗ kế.
SEQ = ["STAND_UP", "LAC1",
       "LAC2", "LAC3", "LAC4", 
       "LAC5", "LAC6", "LAC7", "LAC8", "LAC9", "LAC10", "LAC11", "LAC12","LAC12", "LAC11", "LAC12", "LAC11", "LAC12", "LAC11", "LAC12", "LAC11",]


def main():
    # Tốc độ: python test_pick_real.py [vel] [ovl]   (mặc định 15 30 = chậm)
    vel = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    ovl = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0

    pts = load_points()
    missing = [n for n in dict.fromkeys(SEQ) if n not in pts]
    if missing:
        print("Thiếu teaching point:", missing, "-> chạy teach_record.py lưu trước.")
        return
    print("Điểm đã có:", list(pts.keys()))
    print("Trình tự:", " -> ".join(SEQ))
    print(f"Tốc độ: vel={vel} ovl={ovl}")

    arm = fleet.get(settings.DEMO_STATION)     # S1
    if not arm.connect():
        print("Không kết nối được robot.")
        return

    # KIỂM TRA VÙNG AN TOÀN (soft limit) TRƯỚC KHI CHẠY
    print("--- Kiểm tra soft limit từng điểm ---")
    bad = False
    for name in dict.fromkeys(SEQ):
        okc, warns = arm.check_joints(pts[name]["joints"])
        print(f"  [{name}] " + ("; ".join(warns) if warns else "OK"))
        if not okc:
            bad = True
    if bad:
        print("=> ⛔ CÓ ĐIỂM VƯỢT VÙNG AN TOÀN — dạy lại điểm đó (teach_record) trước khi chạy.")
        return

    input(f"Sẵn sàng? Tay gần E-stop, vùng trống. Enter để chạy (vel{vel} ovl{ovl})... ")
    ok = arm.run_sequence(SEQ, vel=vel, ovl=ovl)
    print("=> KẾT QUẢ:", "OK — robot chạy hết trình tự" if ok else "LỖI (xem log)")


if __name__ == "__main__":
    main()
