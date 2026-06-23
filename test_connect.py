"""Test kết nối robot thật — CHỈ ĐỌC, robot KHÔNG di chuyển.
Chạy: .venv\\Scripts\\python test_connect.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app", "robot", "sdk"))

import robot_sdk_core

IP = "192.168.58.2"
print(f"[1] Đang kết nối {IP} ...")
r = robot_sdk_core.RPC(IP)
print("    ✅ Tạo RPC xong")

try:
    print("[2] SDK version     :", r.GetSDKVersion())
except Exception as e:
    print("    GetSDKVersion lỗi:", e)
try:
    print("[3] Software version:", r.GetSoftwareVersion())
except Exception as e:
    print("    GetSoftwareVersion lỗi:", e)
try:
    print("[4] Góc 6 khớp      :", r.GetActualJointPosDegree())
except Exception as e:
    print("    GetActualJointPosDegree lỗi:", e)
try:
    print("[5] TCP pose        :", r.GetActualTCPPose())
except Exception as e:
    print("    GetActualTCPPose lỗi:", e)

print("\n=> Nếu thấy version + góc khớp = SERVICE đã nói chuyện được với robot thật (chưa di chuyển).")
