"""Test SERVICE noi robot that bang chinh code fleet - CHI DOC (robot khong di chuyen).
Chay: .venv\\Scripts\\python test_fleet.py
"""
from app.robot.fleet import fleet

s1 = fleet.get("S1")          # cánh tay trạm S1 (IP từ .env = 192.168.58.2)
print("Connect S1 ...")
ok = s1.connect()             # connect() trong service goi robot_sdk_core.RPC + GetSDKVersion
print("connected =", ok)
print("state     =", s1.get_state())   # doc goc 6 khop that
print("\n=> connected=True + co goc khop = SERVICE (qua fleet) da dieu khien duoc robot that.")
