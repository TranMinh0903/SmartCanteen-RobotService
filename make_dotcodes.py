"""Sinh ảnh mã (QR hoặc Data Matrix) để dán lên nắp hộp / chiếu vào webcam.

Chạy:
  .venv\\Scripts\\python make_dotcodes.py                  # QR, danh sách mặc định
  .venv\\Scripts\\python make_dotcodes.py CA_KHO COM CANH   # QR, tự chọn
  .venv\\Scripts\\python make_dotcodes.py --dm             # Data Matrix (mã chấm vuông)
  .venv\\Scripts\\python make_dotcodes.py --dm CA_KHO COM   # Data Matrix, tự chọn

Ảnh lưu ./dotcodes/<qr|dm>/<TEN>.png — mỗi ảnh là 1 mã + chữ tên ở dưới.
Nội dung = ĐỊNH DANH MÓN (khớp với cái service verify/đếm).
"""
import os
import sys
import cv2
import numpy as np

DEFAULT = ["CA_KHO", "CA_CHIEN", "THIT_KHO", "THIT_CHIEN", "PHO", "HU_TIU", "COM_GA", "SALAD"]
SIZE = 480           # cạnh mã (px)
QUIET = 40           # viền trắng (quiet zone) — BẮT BUỘC để đọc được
LABEL_H = 70


def base_code(text: str, kind: str):
    """Trả ảnh mã (BGR) chưa viền/nhãn."""
    if kind == "dm":
        from app.vision.codes import encode_datamatrix
        img = encode_datamatrix(text)
        if img is None:
            raise RuntimeError("pylibdmtx chưa cài. Chạy: pip install pylibdmtx \"setuptools<74\"")
        return cv2.resize(img, (SIZE, SIZE), interpolation=cv2.INTER_NEAREST)
    enc = cv2.QRCodeEncoder.create()
    qr = enc.encode(text)
    qr = cv2.resize(qr, (SIZE, SIZE), interpolation=cv2.INTER_NEAREST)
    return cv2.cvtColor(qr, cv2.COLOR_GRAY2BGR)


def make_one(text: str, kind: str, out_dir: str):
    code = base_code(text, kind)
    code = cv2.copyMakeBorder(code, QUIET, QUIET, QUIET, QUIET,
                              cv2.BORDER_CONSTANT, value=(255, 255, 255))
    w = code.shape[1]
    label = np.full((LABEL_H, w, 3), 255, np.uint8)
    cv2.putText(label, text, (QUIET, LABEL_H - 24),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    img = np.vstack([code, label])
    path = os.path.join(out_dir, f"{text}.png")
    cv2.imwrite(path, img)
    return path


def main():
    args = sys.argv[1:]
    kind = "dm" if "--dm" in args else "qr"
    items = [a for a in args if not a.startswith("-")] or DEFAULT
    out_dir = os.path.join(os.path.dirname(__file__), "dotcodes", kind)
    os.makedirs(out_dir, exist_ok=True)
    for t in items:
        print("tạo:", make_one(t, kind, out_dir))
    label = "Data Matrix" if kind == "dm" else "QR"
    print(f"\nXong {len(items)} mã {label} trong: {out_dir}")
    print("Mở 1 ảnh phóng to trên màn hình rồi chĩa webcam vào, hoặc in ra dán nắp hộp.")
    print("Test đọc:  .venv\\Scripts\\python scan_dotcode.py")


if __name__ == "__main__":
    main()
