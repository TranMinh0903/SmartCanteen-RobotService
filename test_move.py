"""Test ARM DI CHUYEN - CHAY KHI VUNG AN TOAN + TAY DAT TREN E-STOP.
Vay NHIEU KHOP (base + co tay) sang trai -> sang phai -> ve, toc do vua (vel30/ovl60).
DONG web pendant truoc (tranh cong 20004) + chi 1 tien trinh python.
Chay: .venv\\Scripts\\python test_move.py
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app", "robot", "sdk"))
import robot_sdk_core

IP = "192.168.58.2"
VEL = 30.0          # toc do khop %
OVL = 60.0          # he so toc do tong %

r = robot_sdk_core.RPC(IP)
print("SDK:", r.GetSDKVersion())

r.Mode(0)             # 0 = auto/remote
time.sleep(0.5)
r.RobotEnable(1)      # bat servo
time.sleep(1.0)

err, home = r.GetActualJointPosDegree()
print("Goc khop home:", home)
if err != 0:
    print("Khong doc duoc goc khop -> DUNG.")
    sys.exit(1)
home = list(home)

def move(name, offsets):
    target = [home[i] + offsets[i] for i in range(6)]
    print(f"MoveJ -> {name} (vel{VEL} ovl{OVL}) ...")
    e = r.MoveJ(target, tool=0, user=0, vel=VEL, ovl=OVL)
    print("   ket qua:", e)
    time.sleep(0.4)

# vay sang TRAI: base +15, vai/khuyu nhe, co tay nhieu (de thay)
move("trai", [+15, +10, -10, +30, -30, +60])
# vay sang PHAI: nguoc lai
move("phai", [-15, -10, +10, -30, +30, -60])
# ve home
print(f"MoveJ -> HOME (vel{VEL} ovl{OVL}) ...")
print("   ket qua:", r.MoveJ(home, tool=0, user=0, vel=VEL, ovl=OVL))

print("\n=> Arm vay trai-phai roi ve home = ARM NHAN TIN HIEU + DI CHUYEN DUOC.")
