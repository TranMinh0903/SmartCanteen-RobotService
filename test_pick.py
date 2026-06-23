"""Cu GAP-DAT hoan chinh - doc 3 teaching point (P_SAFE, P_PICK, P_PLACE) + MoveCart.
Trinh tu: SAFE -> tren PICK -> PICK -> [dong kep] -> len -> tren PLACE -> PLACE -> [mo kep] -> len -> SAFE.

TRUOC KHI CHAY:
  - Day 3 point tren web UI: P_SAFE, P_PICK, P_PLACE
  - De TOC DO TONG (web UI) ~40% (cu dong lon hon, chay cham cho an toan)
  - Don vung trong + cam E-STOP
  - USE_GRIPPER=False: chi chay tay (khong kep) de test quy dao truoc.
    Sau khi test gripper OK -> doi True de gap that.
Chay: .venv\\Scripts\\python test_pick.py
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app", "robot", "sdk"))
import robot_sdk_core

IP = "192.168.58.2"
VEL = 20.0            # toc do lenh (con nhan voi global override tren web UI)
APPROACH_DZ = 80.0    # diem tiep can: tren diem gap/dat 80mm
USE_GRIPPER = False   # True khi gripper da test OK
GRIP_DO_ID = 0

r = robot_sdk_core.RPC(IP)
r.Mode(0); time.sleep(0.5)
r.RobotEnable(1); time.sleep(1.0)


def get_point(name):
    """Doc teaching point -> pose Cartesian [x,y,z,rx,ry,rz] (6 so dau)."""
    err, data = r.GetRobotTeachingPoint(name)
    if err != 0 or not data:
        raise RuntimeError(f"Khong doc duoc point '{name}' (err={err}). Da day chua?")
    vals = [float(x) for x in str(data).split(",")[:6]]
    return vals


def above(pose, dz):
    p = list(pose); p[2] += dz; return p


def moveto(pose, label):
    print(f"  MoveCart -> {label}: {[round(v,1) for v in pose]}")
    e = r.MoveCart(pose, 0, 0, vel=VEL)
    if e != 0:
        raise RuntimeError(f"MoveCart loi ({label}) err={e}")
    time.sleep(0.3)


def grip(close):
    if not USE_GRIPPER:
        print(f"  (gripper OFF) -> bo qua {'DONG' if close else 'MO'} kep")
        return
    r.SetToolDO(GRIP_DO_ID, 1 if close else 0)
    time.sleep(1.0)


print("Doc 3 diem ...")
SAFE  = get_point("P_SAFE")
PICK  = get_point("P_PICK")
PLACE = get_point("P_PLACE")

print(">>> Bat dau cu GAP-DAT (nhin robot, tay tren e-stop) ...")
moveto(SAFE, "SAFE")
moveto(above(PICK, APPROACH_DZ), "tren PICK")
grip(False)                          # mo kep
moveto(PICK, "PICK (ha xuong)")
grip(True)                           # dong kep (gap)
moveto(above(PICK, APPROACH_DZ), "nang len")
moveto(above(PLACE, APPROACH_DZ), "tren PLACE")
moveto(PLACE, "PLACE (ha xuong)")
grip(False)                          # mo kep (tha)
moveto(above(PLACE, APPROACH_DZ), "nang len")
moveto(SAFE, "ve SAFE")

print("\n=> Xong 1 cu GAP-DAT. (USE_GRIPPER=False -> chi chay tay; doi True de gap that.)")
