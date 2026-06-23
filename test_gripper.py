"""Test GRIPPER (kep gap) - dieu khien bang Tool Digital Output (giong du an co).
SetToolDO(id, status): status 1 = DONG kep, 0 = MO kep.
NHIN VAO KEP o dau canh tay khi chay. GIU TAY/NGON XA HAM KEP (kep co the bop).
Chay: .venv\\Scripts\\python test_gripper.py
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app", "robot", "sdk"))
import robot_sdk_core

IP = "192.168.58.2"
DO_ID = 0          # neu khong tac dung -> doi thanh 1 (hoac 2) tuy wiring

r = robot_sdk_core.RPC(IP)
r.Mode(0); time.sleep(0.5)
r.RobotEnable(1); time.sleep(1.0)

print(f">>> NHIN HAM KEP! (dung Tool DO id={DO_ID})")
print("MO kep ...")
print("  SetToolDO ket qua:", r.SetToolDO(DO_ID, 0)); time.sleep(2.0)
print("DONG kep (gap) ...")
print("  SetToolDO ket qua:", r.SetToolDO(DO_ID, 1)); time.sleep(2.0)
print("MO lai ...")
print("  SetToolDO ket qua:", r.SetToolDO(DO_ID, 0)); time.sleep(2.0)

print("\n=> Neu ham kep mo-dong-mo = GRIPPER chay duoc.")
print("   Neu KHONG nhuc nhich: doi DO_ID = 1 (hoac 2) trong file roi chay lai,")
print("   hoac kiem tra day kep + IO status tren web UI.")
