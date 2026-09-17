# language: Python 3.11, file: watcher.py
# Railway-ready Discord username watcher.
# env vars:
#   DISCORD_WEBHOOK_URL   required. full webhook URL
#   DISCORD_AUTH_TOKEN    optional. user token for reliable availability
#   USERNAMES             required. comma-separated
#   POLL_INTERVAL         optional. default 30
#   JITTER                optional. default 5
#   PING_EVERYONE         optional. "true"/"false", default true
#   HEALTHCHECK_PORT      optional. default 8080

import os
import json
import time
import random
import signal
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("watcher")

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
AUTH_TOKEN = os.environ.get("DISCORD_AUTH_TOKEN", "").strip()
USERNAMES_RAW = os.environ.get("USERNAMES", "").strip()
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "30"))
JITTER = int(os.environ.get("JITTER", "5"))
PING_EVERYONE = os.environ.get("PING_EVERYONE", "true").lower() == "true"
HEALTHCHECK_PORT = int(os.environ.get("HEALTHCHECK_PORT", "8080"))

USERNAMES = [u.strip() for u in USERNAMES_RAW.split(",") if u.strip()]

STATE = {
    "started_at": time.time(),
    "last_sweep": 0.0,
    "sweeps": 0,
    "available_hits": 0,
    "last_error": None,
    "alive": True,
}
STATE_LOCK = threading.Lock()

AVAILABILITY_URL = (
    "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
)

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
}
if AUTH_TOKEN:
    HEADERS["Authorization"] = AUTH_TOKEN


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/healthz"):
            self.send_response(404); self.end_headers(); return
        with STATE_LOCK:
            body = json.dumps({
                "ok": STATE["alive"],
                "uptime_s": int(time.time() - STATE["started_at"]),
                "sweeps": STATE["sweeps"],
                "last_sweep_s_ago": (
                    int(time.time() - STATE["last_sweep"])
                    if STATE["last_sweep"] else None
                ),
                "available_hits": STATE["available_hits"],
                "watching": len(USERNAMES),
                "last_error": STATE["last_error"],
            }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass


def start_health_server():
    server = HTTPServer(("0.0.0.0", HEALTHCHECK_PORT), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info(f"healthcheck listening on :{HEALTHCHECK_PORT}/healthz")


def check_username(username, session):
    payload = {"username": username}
    for attempt in range(3):
        try:
            r = session.post(AVAILABILITY_URL, headers=HEADERS,
                             data=json.dumps(payload), timeout=10)
        except requests.RequestException as e:
            log.warning(f"network error for {username}: {e}"); return None
        if r.status_code == 200:
            return not r.json().get("taken", True)
        if r.status_code == 429:
            ra = float(r.headers.get("Retry-After", 5))
            log.info(f"429 on {username}, sleeping {ra}s ({attempt + 1}/3)")
            time.sleep(ra); continue
        if r.status_code in (401, 403):
            log.error(f"auth rejected ({r.status_code}) — check DISCORD_AUTH_TOKEN")
            return None
        log.warning(f"unexpected {r.status_code} for {username}: {r.text[:200]}")
        return None
    return None


def notify_webhook(username, session):
    content = (
        f"@everyone **`{username}`** is now available on Discord."
        if PING_EVERYONE
        else f"**`{username}`** is now available on Discord."
    )
    try:
        r = session.post(WEBHOOK_URL,
                         json={"content": content, "username": "username-watcher"},
                         timeout=10)
        if r.status_code in (200, 204):
            log.info(f"notified webhook: {username}")
            with STATE_LOCK: STATE["available_hits"] += 1
        else:
            log.warning(f"webhook returned {r.status_code}: {r.text[:200]}")
    except requests.RequestException as e:
        log.error(f"webhook send failed for {username}: {e}")


_shutdown = threading.Event()

def _handle_signal(signum, frame):
    log.info(f"signal {signum} received, shutting down")
    _shutdown.set()


def main():
    if not WEBHOOK_URL or "XXXX" in WEBHOOK_URL:
        raise SystemExit("DISCORD_WEBHOOK_URL is required and must be real")
    if not USERNAMES:
        raise SystemExit("USERNAMES is required (comma-separated)")

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    start_health_server()

    log.info(f"watching {len(USERNAMES)} usernames: {USERNAMES}")
    log.info(f"poll interval {POLL_INTERVAL}s (+0..{JITTER}s jitter), "
             f"mention={'on' if PING_EVERYONE else 'off'}")

    state = {u: None for u in USERNAMES}
    session = requests.Session()

    while not _shutdown.is_set():
        for username in USERNAMES:
            if _shutdown.is_set(): break
            available = check_username(username, session)
            if available is None:
                with STATE_LOCK:
                    STATE["last_error"] = f"{username}: check failed"
                continue
            was = state[username]
            if available and was is not True:
                log.info(f"{username} AVAILABLE")
                notify_webhook(username, session)
            elif not available and was is True:
                log.info(f"{username} taken again")
            state[username] = available
            time.sleep(1.2)
        with STATE_LOCK:
            STATE["last_sweep"] = time.time()
            STATE["sweeps"] += 1
        _shutdown.wait(timeout=POLL_INTERVAL + random.uniform(0, JITTER))

    with STATE_LOCK:
        STATE["alive"] = False
    log.info("stopped")


if __name__ == "__main__":
    main()