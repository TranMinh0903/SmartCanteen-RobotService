"""Doc trang thai robot - KHONG di chuyen. Chan doan vi sao khong xoay."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app", "robot", "sdk"))
import robot_sdk_core

r = robot_sdk_core.RPC("192.168.58.2")
print("SDK        :", r.GetSDKVersion())
print("Mode(0)    :", r.Mode(0), "(0 = OK; khac 0 = khong vao auto mode)")
time.sleep(0.3)
print("RobotEnable(1):", r.RobotEnable(1), "(0 = OK; khac 0 = khong enable duoc servo)")
time.sleep(0.3)
err, j = r.GetActualJointPosDegree()
print("Goc 6 khop :", [round(x, 1) for x in j])
print("KHOP 6 hien tai:", round(j[5], 1), "do")
try:
    print("RealTimeState:", r.GetRobotRealTimeState())
except Exception as e:
    print("RealTimeState loi:", e)
