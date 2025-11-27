import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from urllib.parse import urlparse, urlunparse

import cv2
import requests
from flask import Flask, Response, abort, jsonify, request

# =========================================================
# URLs públicas (strings para reuso em memória)
# =========================================================
PUBLIC_TUNNEL_URL = None   # ex.: https://xxxx.trycloudflare.com
PUBLIC_VIDEO_URL = None    # ex.: https://xxxx.trycloudflare.com/video.mjpg?token=...


def get_public_video_url():
    return PUBLIC_VIDEO_URL


# URL padrão do backend (pode sobrescrever com env ou --backend-url)
BACKEND_URL_DEFAULT = os.environ.get(
    "ARDUINO_BACKEND_URL",
    "http://127.0.0.1:8000/api/arduino/pacote/"
)

# =========================
# Helpers IP Webcam
# =========================
def _normalize_ip_webcam_url(url: str) -> str:
    p = urlparse(url)
    if not p.scheme:
        url = "http://" + url
        p = urlparse(url)

    netloc = p.netloc
    if netloc and ":" not in netloc:
        netloc = f"{netloc}:8080"

    path = p.path or "/video"

    # Corrige precedência do operador: se o path for /video e não tiver query, usa type=mpjpeg
    if path == "/video":
        query = p.query or "type=mpjpeg"
    else:
        query = p.query

    new = p._replace(netloc=netloc, path=path, query=query)
    return urlunparse(new)


def _candidate_urls(url: str):
    p = urlparse(_normalize_ip_webcam_url(url))
    base = f"{p.scheme}://{p.netloc}"

    candidates = [urlunparse(p)]
    for path in [
        "/video?type=mpjpeg",
        "/video",
        "/?action=stream",
        "/mjpegfeed",
        "/cam.mjpg",
        "/stream.mjpg",
    ]:
        candidates.append(f"{base}{path}")

    seen, uniq = set(), []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


# =========================
# Captura cross-plataforma
# =========================
def open_capture(source):
    """
    Abre a captura de forma adequada para cada SO.
    - Windows: usa CAP_DSHOW
    - macOS: usa CAP_AVFOUNDATION
    - Linux/outros: backend padrão
    """
    if isinstance(source, int):
        if sys.platform.startswith("win"):
            # Windows
            return cv2.VideoCapture(source, cv2.CAP_DSHOW)
        elif sys.platform == "darwin":
            # macOS
            return cv2.VideoCapture(source, cv2.CAP_AVFOUNDATION)
        else:
            # Linux / outros
            return cv2.VideoCapture(source)
    else:
        # Para URLs de stream/IP Webcam, deixa o backend padrão.
        cap = cv2.VideoCapture(source)
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        return cap


def open_stream_with_fallback(url: str):
    urls = _candidate_urls(url)
    last_cap = None
    for u in urls:
        cap = open_capture(u)
        if cap.isOpened():
            ok, _ = cap.read()
            if ok:
                return cap
            cap.release()
        last_cap = cap
    if last_cap:
        last_cap.release()
    return None


# =========================
# Captura em thread
# =========================
class Camera:
    def __init__(self, source, fps=12, width=None, height=None):
        self.cap = open_capture(source) if isinstance(source, int) else open_stream_with_fallback(source)
        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError("Não foi possível abrir a câmera/stream.")

        if width:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
        if height:
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))

        self.fps = max(1, int(fps))
        self._ret = False
        self._frame = None
        self._lock = Lock()
        self._stop = Event()
        self._t = Thread(target=self._reader, daemon=True)
        self._t.start()

    def _reader(self):
        while not self._stop.is_set():
            ret, frame = self.cap.read()
            if ret:
                with self._lock:
                    self._ret = True
                    self._frame = frame
            else:
                time.sleep(0.25)
            time.sleep(1.0 / self.fps)

    def get_frame(self):
        with self._lock:
            if not self._ret or self._frame is None:
                return None
            return self._frame.copy()

    def release(self):
        self._stop.set()
        try:
            self._t.join(timeout=1.0)
        except Exception:
            pass
        try:
            self.cap.release()
        except Exception:
            pass


# =========================
# Leitor de QR (thread) — QR "regiao:nome" (com fallback p/ "regiao-nome")
# =========================
class QRReader:
    def __init__(self, cam: Camera, min_log_interval=2.0, backend_url: str | None = None):
        self.cam = cam
        self.detector = cv2.QRCodeDetector()
        self.min_log_interval = float(min_log_interval)

        self.backend_url = backend_url

        self.last_raw = None            # string inteira do QR (ex.: "sul:paraiba")
        self.last_regiao = None         # parte antes do separador
        self.last_nome = None           # parte depois do separador
        self.last_codigo = None         # ISO UTC da leitura (renomeado para 'codigo')
        self.last_pts = None
        self.last_time = 0.0

        self._stop = Event()
        self._lock = Lock()
        self._t = Thread(target=self._loop, daemon=True)
        self._t.start()

    @staticmethod
    def _parse_qr(text: str):
        """
        Parse do QR.
        Formato principal:  "regiao:nome"
        Fallback legado:    "regiao-nome"
        Se não tiver separador, considera tudo como regiao.
        """
        if not text:
            return None, None

        t = text.strip()
        if ":" in t:
            regiao, nome = t.split(":", 1)
        elif "-" in t:
            # fallback para formato antigo "regiao-nome"
            regiao, nome = t.split("-", 1)
        else:
            # sem separador: tudo vira regiao
            return (t or "").strip() or None, None

        regiao = (regiao or "").strip() or None
        nome = (nome or "").strip() or None
        return regiao, nome

    def _send_to_backend(self, payload: dict):
        """
        Envia o objeto lido para o backend Django (POST JSON).
        Agora com logs mais detalhados.
        """
        if not self.backend_url:
            print("[BACKEND] URL não configurada, não enviando.", flush=True)
            return

        url = str(self.backend_url).strip()
        if not url:
            print("[BACKEND] URL vazia após strip(), não enviando.", flush=True)
            return
        if not url.endswith("/"):
            url += "/"

        try:
            print(f"[BACKEND] Enviando para {url}: {payload}", flush=True)
            resp = requests.post(url, json=payload, timeout=5)
            print(f"[BACKEND] Resposta {resp.status_code}: {resp.text[:200]!r}", flush=True)
            resp.raise_for_status()
        except Exception as e:
            print(f"[BACKEND ERRO] {e}", flush=True)

    def _loop(self):
        while not self._stop.is_set():
            frame = self.cam.get_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            data, points, _ = self.detector.detectAndDecode(frame)

            with self._lock:
                self.last_pts = points.reshape(-1, 2).astype(int) if points is not None and len(points) > 0 else None
                now = time.time()
                if data and (data != self.last_raw or (now - self.last_time) > self.min_log_interval):
                    regiao, nome = self._parse_qr(data)
                    ts_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")  # usamos como 'codigo'

                    self.last_raw = data
                    self.last_regiao = regiao
                    self.last_nome = nome
                    self.last_codigo = ts_iso
                    self.last_time = now

                    print(f"[QR LIDO] {data}", flush=True)  # único log de QR

                    # monta o objeto e envia para o backend
                    payload = {
                        "regiao": regiao,
                        "nome": nome,
                        "codigo": ts_iso,
                    }
                    self._send_to_backend(payload)

            time.sleep(0.02)

    def get_overlay(self):
        with self._lock:
            return self.last_raw, (None if self.last_pts is None else self.last_pts.copy())

    def get_last_obj(self):
        with self._lock:
            return {
                "regiao": self.last_regiao,
                "nome": self.last_nome,
                "codigo": self.last_codigo,
            }

    def stop(self):
        self._stop.set()
        try:
            self._t.join(timeout=1.0)
        except Exception:
            pass


# =========================
# Flask (MJPEG)
# =========================
app = Flask(__name__)


def _check_token():
    token = app.config.get("STREAM_TOKEN")
    return True if not token else (request.args.get("token") == token)


def mjpeg_generator(cam: Camera, jpeg_quality=80):
    boundary = b"--frame"
    while True:
        frame = cam.get_frame()
        if frame is None:
            time.sleep(0.05)
            continue

        qr = app.config.get("QR_READER")
        if qr is not None:
            raw, pts = qr.get_overlay()
            if pts is not None and len(pts) > 0:
                for i in range(len(pts)):
                    p1 = tuple(pts[i])
                    p2 = tuple(pts[(i + 1) % len(pts)])
                    cv2.line(frame, p1, p2, (0, 255, 0), 2)
            if raw:
                shown = raw[:60] + ("..." if len(raw) > 60 else "")
                cv2.putText(
                    frame,
                    shown,
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2,
                )

        ok, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)])
        if not ok:
            continue

        yield (
            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
            + jpg.tobytes()
            + b"\r\n"
        )


@app.route("/")
def index():
    token = app.config.get("STREAM_TOKEN")
    tip = "/video.mjpg" + (f"?token={token}" if token else "")
    return f"OK: acesse {tip}"


@app.route("/video.mjpg")
def video_mjpg():
    if not _check_token():
        abort(401)
    cam: Camera = app.config["CAMERA"]
    resp = Response(
        mjpeg_generator(cam, jpeg_quality=app.config.get("JPEG_QUALITY", 80)),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Connection"] = "keep-alive"
    return resp


@app.route("/last_code")
def last_code():
    """Retorna {regiao, nome, codigo} do último QR lido (em memória)."""
    qr = app.config.get("QR_READER")
    if not qr:
        return jsonify({"regiao": None, "nome": None, "codigo": None})
    return jsonify(qr.get_last_obj())


# =========================
# Cloudflared Quick Tunnel (assíncrono e silencioso)
# =========================
def start_quick_tunnel_async(
    port: int,
    token: str | None,
    protocol: str = "http2",
    ha_connections: int = 4,
    cf_path: str | None = None,
):
    """
    Sobe o cloudflared e, quando a URL aparecer nos logs, popula as strings
    e imprime exatamente um log: [PUBLIC_VIDEO_URL] <url>.
    """
    cf_bin = cf_path or shutil.which("cloudflared")
    if not cf_bin:
        raise RuntimeError("cloudflared não encontrado no PATH.")

    args = [
        cf_bin,
        "tunnel",
        "--url",
        f"http://127.0.0.1:{port}",
        "--protocol",
        protocol,
        "--ha-connections",
        str(ha_connections),
    ]

    # No macOS e Linux, creationflags = 0; no Windows usamos CREATE_NO_WINDOW.
    creationflags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW

    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=creationflags,
    )

    def _reader():
        global PUBLIC_TUNNEL_URL, PUBLIC_VIDEO_URL
        try:
            for line in proc.stdout:
                m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
                if m and PUBLIC_TUNNEL_URL is None:
                    PUBLIC_TUNNEL_URL = m.group(0)
                    tip = "/video.mjpg" + (f"?token={token}" if token else "")
                    PUBLIC_VIDEO_URL = PUBLIC_TUNNEL_URL + tip
                    print(f"[PUBLIC_VIDEO_URL] {PUBLIC_VIDEO_URL}", flush=True)  # único log do túnel
                    break
        except Exception:
            pass

    Thread(target=_reader, daemon=True).start()
    return proc


def stop_quick_tunnel(proc):
    if not proc:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception:
        pass


def _graceful_exit(camera: Camera):
    try:
        qr = app.config.get("QR_READER")
        if qr:
            qr.stop()
    except Exception:
        pass
    try:
        cf_proc = app.config.get("CF_PROC")
        if cf_proc:
            stop_quick_tunnel(cf_proc)
    except Exception:
        pass
    camera.release()
    os._exit(0)


# =========================
# Main
# =========================
def main():
    parser = argparse.ArgumentParser(
        description=(
            "MJPEG da câmera (QR 'regiao:nome' + Tunnel) com armazenamento em "
            "memória e envio para backend."
        )
    )
    parser.add_argument("--source", default="0")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--jpeg-quality", type=int, default=80)
    parser.add_argument("--token", default=os.environ.get("STREAM_TOKEN"))
    parser.add_argument("--tunnel", action="store_true")
    parser.add_argument("--cloudflared", default=None)
    parser.add_argument("--tunnel-protocol", default="http2", choices=["quic", "http2"])
    parser.add_argument("--tunnel-ha", type=int, default=4)
    parser.add_argument(
        "--backend-url",
        default=BACKEND_URL_DEFAULT,
        help="URL para enviar o objeto lido do QR (POST JSON).",
    )

    args = parser.parse_args()

    # Normaliza a backend-url (evita problemas com espaços e falta de /)
    if args.backend_url:
        args.backend_url = args.backend_url.strip()
        if args.backend_url and not args.backend_url.endswith("/"):
            args.backend_url += "/"

    source = int(args.source) if args.source.isdigit() else args.source

    camera = Camera(source, fps=args.fps, width=args.width, height=args.height)
    app.config["CAMERA"] = camera
    app.config["STREAM_TOKEN"] = args.token
    app.config["JPEG_QUALITY"] = args.jpeg_quality

    qr_reader = QRReader(
        camera,
        min_log_interval=2.0,
        backend_url=args.backend_url,
    )
    app.config["QR_READER"] = qr_reader

    signal.signal(signal.SIGINT, lambda *_: _graceful_exit(camera))

    if args.tunnel:
        try:
            cf_proc = start_quick_tunnel_async(
                port=args.port,
                token=args.token,
                protocol=args.tunnel_protocol,
                ha_connections=args.tunnel_ha,
                cf_path=args.cloudflared,
            )
            app.config["CF_PROC"] = cf_proc
        except Exception:
            # se der erro no túnel, apenas segue com o server local
            pass

    try:
        app.run(host=args.host, port=args.port, debug=False, threaded=True)
    finally:
        try:
            qr = app.config.get("QR_READER")
            if qr:
                qr.stop()
        except Exception:
            pass
        try:
            stop_quick_tunnel(app.config.get("CF_PROC"))
        except Exception:
            pass
        camera.release()


if __name__ == "__main__":
    main()
