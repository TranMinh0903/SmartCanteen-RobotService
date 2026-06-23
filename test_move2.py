"""Test DI CHUYEN - xoay khop 6 (co tay) 90 do va GIU NGUYEN (KHONG quay ve cho cu).
NHIN VAO CO TAY ROBOT khi chay. Chay khi vung an toan + cam e-stop.
Chay: .venv\\Scripts\\python test_move2.py
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app", "robot", "sdk"))
import robot_sdk_core

IP = "192.168.58.2"
ANGLE = -90.0         # xoay NGUOC (khop 6 dang gan dinh + 122.5 -> xoay xuong 32.5, an toan)

r = robot_sdk_core.RPC(IP)
print("ResetAllError:", r.ResetAllError()); time.sleep(0.5)   # xoa alarm cu (vd overrun)
print("Mode(0)      :", r.Mode(0)); time.sleep(0.5)
print("RobotEnable  :", r.RobotEnable(1)); time.sleep(1.0)

err, before = r.GetActualJointPosDegree()
print("KHOP 6 TRUOC:", round(before[5], 2), "do")

print(f">>> NHIN CO TAY ROBOT! Xoay +{ANGLE} do ...")
target = list(before); target[5] += ANGLE
e = r.MoveJ(target, tool=0, user=0, vel=83.0, ovl=100.0)
print("  ket qua MoveJ:", e, "(0 = OK)")
time.sleep(2.0)

err, after = r.GetActualJointPosDegree()
print("KHOP 6 SAU :", round(after[5], 2), "do")
print("=> Lech:", round(after[5] - before[5], 2), "do")

print("\n=> Robot DA XOAY va GIU NGUYEN (khong quay ve).")
print("   Chay lai = xoay tiep +90 nua tu cho hien tai (toi gioi han khop thi MoveJ tra err != 0).")
