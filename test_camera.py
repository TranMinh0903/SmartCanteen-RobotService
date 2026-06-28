"""Test WEBCAM (HIKVISION USB) — xem hinh + nhan QR chen + ArUco khay.

Chay:
  .venv\\Scripts\\python test_camera.py --list        # liet ke camera
  .venv\\Scripts\\python test_camera.py --probe 1      # DO to hop (backend x fourcc x res) chay duoc -> chong man den
  .venv\\Scripts\\python test_camera.py 1              # mo cam index 1 (MJPG, DirectShow)
  .venv\\Scripts\\python test_camera.py 1 --msmf       # dung backend MSMF (neu DSHOW den)
  .venv\\Scripts\\python test_camera.py 1 --res 640x480

Trong cua so:  q = thoat,  s = luu anh.
Khung XANH = QR (in console),  khung CAM = ArUco marker (cho pose khay).

MAN HINH DEN + FPS thap (0.9) = sai dinh dang. Chay '--probe' de tim FOURCC dung
(thuong la MJPG). Tool nay mac dinh da ep MJPG + ham nong khung.
"""
import sys
import time
import cv2


def fourcc_str(v):
    v = int(v)
    return "".join(chr((v >> (8 * i)) & 0xFF) for i in range(4))


def open_cam(idx, backend, fourcc, w, h):
    cap = cv2.VideoCapture(idx, backend)
    if not cap.isOpened():
        return None
    if fourcc:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
    if w and h:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
    cap.set(cv2.CAP_PROP_FPS, 30)
    # ham nong: bo vai khung dau (cam hay den o khung dau)
    for _ in range(8):
        cap.read()
    return cap


def list_cameras(max_idx=6):
    print("Quet camera 0..%d (DirectShow)..." % max_idx)
    found = []
    for i in range(max_idx + 1):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            r, _ = cap.read()
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"  [index {i}] MO DUOC  {w}x{h}  doc-frame={'OK' if r else 'loi'}")
            if r:
                found.append(i)
        cap.release()
    print(f"  -> Camera dung duoc: {found}" if found else "  -> KHONG thay camera.")
    return found


def probe(idx):
    """Dò backend x fourcc x res -> bao to hop nao cho hinh SANG (khong den)."""
    backends = [("DSHOW", cv2.CAP_DSHOW), ("MSMF", cv2.CAP_MSMF)]
    fourccs = ["MJPG", "YUY2", ""]            # "" = de mac dinh
    reses = [(1280, 720), (640, 480)]
    print(f"=== PROBE camera index {idx} ===")
    print(f"{'backend':7} {'fourcc_set':10} {'fourcc_real':11} {'res':10} {'fps':5} {'brightness':10} ket_qua")
    good = []
    for bname, b in backends:
        for fc in fourccs:
            for (w, h) in reses:
                cap = open_cam(idx, b, fc, w, h)
                if cap is None:
                    print(f"{bname:7} {fc or '(def)':10} {'-':11} {f'{w}x{h}':10} {'-':5} {'-':10} KHONG MO")
                    continue
                ok, frame = cap.read()
                if not ok or frame is None:
                    print(f"{bname:7} {fc or '(def)':10} {'-':11} {f'{w}x{h}':10} {'-':5} {'-':10} KHONG DOC")
                    cap.release()
                    continue
                real_fc = fourcc_str(cap.get(cv2.CAP_PROP_FOURCC))
                rw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                rh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                bright = float(frame.mean())
                verdict = "DEN" if bright < 6 else "OK <-- dung duoc"
                if bright >= 6:
                    good.append((bname, fc, rw, rh))
                print(f"{bname:7} {fc or '(def)':10} {real_fc:11} {f'{rw}x{rh}':10} {fps:<5.0f} {bright:<10.1f} {verdict}")
                cap.release()
    print()
    if good:
        # uu tien MSMF (chay moi do phan giai) + res lon nhat
        good.sort(key=lambda g: (g[0] != "MSMF", -(g[2] * g[3])))
        b, fc, w, h = good[0]
        flag = " --msmf" if b == "MSMF" else ""
        print(f"=> Chay:  python test_camera.py {idx}{flag} --res {w}x{h}   (fourcc {fc or 'default'}, backend {b})")
    else:
        print("=> Tat ca DEN. Thu: rut/cam lai USB, kiem tra app HIKVISION co dang chiem cam khong,")
        print("   hoac cam can anh sang. Co the cam la loai IP (RTSP) chu khong phai UVC.")
    return good


def make_aruco():
    try:
        d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        return ("new", cv2.aruco.ArucoDetector(d, cv2.aruco.DetectorParameters()), d, None)
    except AttributeError:
        d = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
        return ("old", None, d, cv2.aruco.DetectorParameters_create())


def detect_aruco(aruco, gray):
    mode, det, d, params = aruco
    if mode == "new":
        return det.detectMarkers(gray)[:2]
    c, i, _ = cv2.aruco.detectMarkers(gray, d, parameters=params)
    return c, i


def view(idx, backend, fourcc, w, h):
    print(f"Mo camera {idx} backend={'MSMF' if backend==cv2.CAP_MSMF else 'DSHOW'} fourcc={fourcc or 'default'} {w}x{h}")
    cap = open_cam(idx, backend, fourcc, w, h)
    if cap is None:
        print(f"KHONG mo duoc camera {idx}. Chay '--probe {idx}'.")
        return
    # TU FALLBACK: neu DSHOW ra khung DEN (cam HIKVISION khong kham 720p qua DSHOW) -> doi MSMF
    ok, frame = cap.read()
    if ok and frame is not None and float(frame.mean()) < 6 and backend == cv2.CAP_DSHOW:
        print("  ! DSHOW ra khung DEN -> tu doi sang MSMF...")
        cap.release()
        backend = cv2.CAP_MSMF
        cap = open_cam(idx, backend, fourcc, w, h)
        if cap is None:
            print("  MSMF cung khong mo duoc. Chay '--probe'."); return
    print(f"  -> backend={'MSMF' if backend==cv2.CAP_MSMF else 'DSHOW'} "
          f"thuc te: fourcc={fourcc_str(cap.get(cv2.CAP_PROP_FOURCC))} "
          f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} "
          f"fps={cap.get(cv2.CAP_PROP_FPS):.0f}")
    qr = cv2.QRCodeDetector()
    aruco = make_aruco()
    print("Nhan 'q' thoat, 's' luu.\n")
    last_qr = ""
    n, t0 = 0, time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Mat frame -> dung.")
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        try:
            data, pts, _ = qr.detectAndDecode(frame)
        except cv2.error:
            data, pts = "", None
        if pts is not None and len(pts) > 0:
            p = pts.astype(int).reshape(-1, 2)
            cv2.polylines(frame, [p], True, (0, 255, 0), 2)
            if data:
                cv2.putText(frame, f"QR: {data}", (p[0][0], max(20, p[0][1] - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                if data != last_qr:
                    print(f"[QR] {data}"); last_qr = data
        corners, ids = detect_aruco(aruco, gray)
        if ids is not None and len(ids) > 0:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
            cv2.putText(frame, "ArUco IDs: " + ",".join(str(int(i)) for i in ids.flatten()),
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 140, 255), 2)
        n += 1
        if n % 30 == 0:
            cv2.setWindowTitle("cam", f"cam idx={idx}  {n/(time.time()-t0):.1f} FPS  (q=thoat s=luu)")
        cv2.imshow("cam", frame)
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        if k == ord('s'):
            fn = f"snapshot_{int(time.time())}.jpg"
            cv2.imwrite(fn, frame); print(f"[luu] {fn}")
    cap.release()
    cv2.destroyAllWindows()


def main():
    args = sys.argv[1:]
    if "--list" in args:
        list_cameras(); return
    if "--probe" in args:
        i = args[args.index("--probe") + 1] if args.index("--probe") + 1 < len(args) else "0"
        probe(int(i)); return

    idx = 0
    backend = cv2.CAP_MSMF if "--msmf" in args else cv2.CAP_DSHOW
    fourcc = "MJPG"
    w, h = 1280, 720
    for a in args:
        if a.isdigit():
            idx = int(a)
        elif "x" in a and a.replace("x", "").isdigit():
            w, h = (int(x) for x in a.split("x"))
        elif a.startswith("--res") and "=" in a:
            w, h = (int(x) for x in a.split("=")[1].split("x"))
    # ho tro '--res 640x480' (tach roi)
    if "--res" in args:
        j = args.index("--res") + 1
        if j < len(args) and "x" in args[j]:
            w, h = (int(x) for x in args[j].split("x"))
    view(idx, backend, fourcc, w, h)


if __name__ == "__main__":
    main()
