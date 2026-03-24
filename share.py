"""
FoodRush -- Quick Public Share (5-10 mins)
Uses Cloudflare Tunnel (no account needed!) to give a public URL.

Usage:
    python share.py              # runs for 10 minutes
    python share.py --minutes 5  # runs for 5 minutes
    python share.py --port 5001  # use a different port
"""

import sys
import time
import argparse
import threading
import webbrowser
from random import randint

# ── Args ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Share FoodRush publicly via Cloudflare")
parser.add_argument("--port",    default=5000, type=int, help="Port (default: 5000)")
parser.add_argument("--minutes", default=10,   type=int, help="Auto-stop after N minutes (default: 10)")
args = parser.parse_args()

PORT         = args.port
MINUTES      = args.minutes
METRICS_PORT = randint(8200, 9000)   # random free metrics port

# ── Load Flask app ─────────────────────────────────────────────────────────────
print()
print("[1/3] Loading FoodRush...")
try:
    from app import app, init_db
    init_db()
    print("[OK]  App and database ready.")
except Exception as e:
    print(f"[ERROR] Could not load app: {e}")
    sys.exit(1)

# ── Open Cloudflare tunnel ─────────────────────────────────────────────────────
print(f"[2/3] Opening Cloudflare tunnel (downloading cloudflared if needed)...")
try:
    from flask_cloudflared import _run_cloudflared
    public_url = _run_cloudflared(PORT, METRICS_PORT)
    print(f"[OK]  Tunnel ready.")
except Exception as e:
    print(f"[ERROR] Cloudflare tunnel failed: {e}")
    print()
    print("  --> Try running your app locally instead:")
    print(f"      python app.py")
    print(f"  --> Then share using VS Code port forwarding or")
    print(f"      download ngrok from: https://ngrok.com/download")
    sys.exit(1)

# ── Banner ─────────────────────────────────────────────────────────────────────
sep = "=" * 64
print()
print(sep)
print("  FoodRush is LIVE! Share the link below with anyone:")
print(sep)
print()
print(f"  >> Public URL  :  {public_url}")
print(f"  >> Local URL   :  http://127.0.0.1:{PORT}")
print()
print(f"  >> Auto-stops in {MINUTES} minute(s)  |  Press Ctrl+C to stop now")
print()
print(sep)
print()

# ── Auto-open local URL in browser ────────────────────────────────────────────
def open_browser():
    time.sleep(2)
    try:
        webbrowser.open(f"http://127.0.0.1:{PORT}")
    except Exception:
        pass

threading.Thread(target=open_browser, daemon=True).start()

# ── Countdown / auto-stop ──────────────────────────────────────────────────────
_cf_process = None
try:
    from flask_cloudflared import _cloudflared_process as _cf_process
except Exception:
    pass

def auto_stop():
    total_sec = MINUTES * 60
    elapsed   = 0

    while elapsed < total_sec:
        sleep_for = min(60, total_sec - elapsed)
        time.sleep(sleep_for)
        elapsed  += sleep_for
        remaining = (total_sec - elapsed) // 60
        if remaining > 0:
            print(f"  [INFO] {remaining} min left -- share: {public_url}")

    print()
    print("  [TIMER] Time is up! Closing tunnel...")
    try:
        from flask_cloudflared import cleanup_cloudflared
        cleanup_cloudflared()
    except Exception:
        pass
    print("  [DONE] Tunnel closed. Run 'python share.py' to start again.")
    import os
    os._exit(0)

threading.Thread(target=auto_stop, daemon=True).start()

# ── Run Flask ──────────────────────────────────────────────────────────────────
print(f"[3/3] Server starting on port {PORT}...")
print()
try:
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
except KeyboardInterrupt:
    print()
    print("  [STOPPED] Stopped by you.")
    try:
        from flask_cloudflared import cleanup_cloudflared
        cleanup_cloudflared()
    except Exception:
        pass
    print("  [DONE] All cleaned up. Goodbye!")
