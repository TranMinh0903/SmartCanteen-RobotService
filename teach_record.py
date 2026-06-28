"""GHI TEACHING POINT bang HAND-GUIDING (keo tay) — luu vao teaching_points.json.

LUONG DUNG:
   1) Dong web pendant + chi 1 tien trinh python (tranh chiem cong 20004).
   2) Chay:  .venv\\Scripts\\python teach_record.py
   3) Go 'drag on'  -> robot mem ra, ban CAM TAY KEO toi vi tri can day.
   4) Go 'save TEN' -> ghi goc khop + toa do TCP hien tai (vi du: save LANE_S1).
   5) Lap lai cho cac diem:  HOME, LANE_S1, PLACE_S1 ...
   6) Go 'drag off' -> khoa lai.  'goto TEN' -> robot tu chay toi diem (vel thap, hoi xac nhan).
   7) 'quit' de thoat.

CAC LENH:
   drag on | drag off       bat/tat che do keo tay (hand-guiding)
   here                     in goc khop + TCP hien tai (khong luu)
   save TEN                 luu diem TEN
   list                     liet ke cac diem da luu
   del TEN                  xoa diem
   goto TEN                 robot tu chay toi diem TEN (CHAM, hoi xac nhan)
   quit
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app", "robot", "sdk"))
import robot_sdk_core  # noqa: E402

IP = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "192.168.58.2"
PointsFile = os.path.join(os.path.dirname(__file__), "teaching_points.json")
GOTO_VEL = 15.0      # toc do khi 'goto' (CHAM cho an toan)
GOTO_OVL = 30.0


def load_points():
    if os.path.exists(PointsFile):
        with open(PointsFile, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_points(pts):
    with open(PointsFile, "w", encoding="utf-8") as f:
        json.dump(pts, f, indent=2, ensure_ascii=False)


_LIMITS = None


def soft_limits(r):
    """Doc soft limit khop -> [(min,max)]x6. Cache."""
    global _LIMITS
    if _LIMITS is None:
        try:
            err, v = r.GetJointSoftLimitDeg()
            _LIMITS = [(v[i * 2], v[i * 2 + 1]) for i in range(6)] if err == 0 and v else []
        except Exception:  # noqa: BLE001
            _LIMITS = []
    return _LIMITS


def check_limits(r, j, margin=3.0):
    """Tra list canh bao neu khop vuot/sat soft limit."""
    lims = soft_limits(r)
    if not lims:
        return []
    out = []
    for i, (a, (lo, hi)) in enumerate(zip(j, lims), start=1):
        if a < lo or a > hi:
            out.append(f"J{i}={a:.1f} VUOT [{lo:.0f},{hi:.0f}]")
        elif a < lo + margin or a > hi - margin:
            out.append(f"J{i}={a:.1f} SAT gioi han [{lo:.0f},{hi:.0f}]")
    return out


def main():
    print(f"Ket noi robot {IP} ...")
    r = robot_sdk_core.RPC(IP)
    print("SDK:", r.GetSDKVersion())
    r.Mode(0)
    time.sleep(0.3)
    r.RobotEnable(1)
    time.sleep(0.8)

    pts = load_points()
    print(f"Da nap {len(pts)} diem tu {os.path.basename(PointsFile)}: {list(pts.keys())}")
    print("Go 'drag on' roi keo tay robot. 'quit' de thoat.\n")

    dragging = False
    while True:
        try:
            line = input("teach> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else None

        if cmd == "quit" or cmd == "exit":
            break

        elif cmd == "drag" and arg in ("on", "off"):
            if arg == "on":
                rcm = r.Mode(1)            # 1 = MANUAL — BAT BUOC de keo tay (drag)
                time.sleep(0.3)
                rc = r.DragTeachSwitch(1)
                dragging = (rc == 0)
                print(f"  Mode(1 manual)->{rcm}  DragTeachSwitch(1)->{rc}  "
                      f"{'(robot MEM - keo tay duoc)' if dragging else '(loi)'}")
                if rcm != 0 or rc != 0:
                    print("  ! Loi. Kiem tra: robot da enable? cong tac MODE tren control box dang AUTO?")
            else:
                rc = r.DragTeachSwitch(0)
                r.Mode(0)                  # ve AUTO de 'goto'/MoveJ chay
                dragging = False
                print(f"  DragTeachSwitch(0)->{rc} + Mode(0 auto) (da khoa)")

        elif cmd == "here":
            err, j = r.GetActualJointPosDegree()
            _, tcp = r.GetActualTCPPose()
            print(f"  joints(err={err}) = {[round(x,2) for x in j]}")
            print(f"  tcp             = {[round(x,2) for x in tcp]}")

        elif cmd == "save" and arg:
            err, j = r.GetActualJointPosDegree()
            if err != 0:
                print(f"  ! Khong doc duoc goc khop (err={err}) -> KHONG luu.")
                continue
            _, tcp = r.GetActualTCPPose()
            pts[arg] = {"joints": [round(float(x), 3) for x in j],
                        "tcp": [round(float(x), 3) for x in tcp],
                        "ts": int(time.time())}
            save_points(pts)
            print(f"  [luu] {arg} = joints {pts[arg]['joints']}")
            for w in check_limits(r, j):
                print(f"  ⚠ {w}")

        elif cmd == "list":
            if not pts:
                print("  (chua co diem nao)")
            for name, p in pts.items():
                print(f"  {name:14s} joints={p['joints']}")

        elif cmd == "check":
            for name, p in pts.items():
                warns = check_limits(r, p["joints"])
                print(f"  {name:14s} " + ("; ".join(warns) if warns else "OK"))

        elif cmd == "del" and arg:
            if arg in pts:
                del pts[arg]
                save_points(pts)
                print(f"  da xoa {arg}")
            else:
                print(f"  khong co diem {arg}")

        elif cmd == "goto" and arg:
            if arg not in pts:
                print(f"  khong co diem {arg}")
                continue
            if dragging:
                print("  ! Dang o che do drag -> go 'drag off' truoc khi goto.")
                continue
            j = pts[arg]["joints"]
            ok = input(f"  Robot SE CHAY toi {arg}={[round(x,1) for x in j]} "
                       f"(vel{GOTO_VEL}). Go 'yes' de chay: ").strip().lower()
            if ok != "yes":
                print("  bo qua.")
                continue
            rc = r.MoveJ(j, tool=0, user=0, vel=GOTO_VEL, ovl=GOTO_OVL)
            print(f"  MoveJ -> {arg}: {rc}")

        else:
            print("  Lenh: drag on|off | here | save TEN | list | check | del TEN | goto TEN | quit")

    if dragging:
        r.DragTeachSwitch(0)
        print("Da tat drag.")
    print("Thoat. Cac diem da luu o teaching_points.json")


if __name__ == "__main__":
    main()
