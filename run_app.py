"""
FoodRush Desktop App Launcher
Run this file to open FoodRush as a native desktop app window.
Usage: python run_app.py
"""
import threading
import time
import webview
from app import app  # Import Flask app

PORT = 5000

def start_flask():
    """Run Flask silently in background thread."""
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)  # Suppress Flask console output
    app.run(port=PORT, debug=False, use_reloader=False, threaded=True)

if __name__ == '__main__':
    # Start Flask in background
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # Wait a moment for Flask to start
    time.sleep(1.5)

    # Open native desktop window
    webview.create_window(
        title='FoodRush 🍔',
        url=f'http://127.0.0.1:{PORT}',
        width=1280,
        height=800,
        min_size=(900, 600),
        resizable=True,
    )
    webview.start()
