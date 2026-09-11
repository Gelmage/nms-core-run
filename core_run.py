#!/usr/bin/env python3
"""
The Run To Core - see which No Man's Sky teleports actually move you inward.

    python3 core_run.py

Finds your save, opens a page in your browser, and keeps it up to date. The game
writes the save when you save or autosave -- typically when you dock, exit a ship
or land -- so the page follows a few seconds behind those moments rather than
tracking you continuously. That is the best any save reader can do.

    python3 core_run.py --save /path/to/save.hg    read a specific file
    python3 core_run.py --interval 60              check for new saves more often
    python3 core_run.py --list                     show every save found
    python3 core_run.py --no-browser               do not open a browser

Read-only. This never writes to your save.
"""
import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import nms_save

# Packaged as a one-file executable, PyInstaller unpacks the bundled data to a
# temporary directory and points sys._MEIPASS at it. Running from source, the page
# simply sits next to this file.
HERE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
PAGE = HERE / "index.html"
DEFAULT_INTERVAL = 120

# A fixed port lets a desktop shortcut notice that the tool is already running and
# just raise the existing window, instead of leaving a pile of dead servers behind.
DEFAULT_PORT = 8787

# Chromium-family browsers can open a URL as a plain window with no tabs and no
# address bar, which is as close to a native application as this needs to get,
# without adding a single dependency.
APP_MODE_BROWSERS = [
    "chromium", "chromium-browser", "google-chrome", "google-chrome-stable",
    "brave-browser", "microsoft-edge", "vivaldi", "thorium-browser",
]
APP_MODE_MACOS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
APP_MODE_WINDOWS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _default_browser_binary():
    """The user's own default browser, if it is Chromium-family.

    Worth the trouble: opening the window in the browser they already use means it
    inherits their profile, theme and extensions, instead of launching a second,
    unfamiliar browser alongside it.
    """
    try:
        out = subprocess.run(["xdg-settings", "get", "default-web-browser"],
                             capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return None
    entry = out.stdout.strip()
    if not entry.endswith(".desktop"):
        return None

    for base in (Path.home() / ".local/share/applications",
                 Path("/usr/share/applications"),
                 Path("/var/lib/flatpak/exports/share/applications")):
        path = base / entry
        if not path.is_file():
            continue
        try:
            for line in path.read_text(errors="replace").splitlines():
                if not line.startswith("Exec="):
                    continue
                # Exec lines carry placeholders like %U; the binary is the first word.
                cmd = line[5:].split()[0].strip('"')
                name = Path(cmd).name
                if any(b in name for b in
                       ("chrome", "chromium", "brave", "edge", "vivaldi")):
                    return shutil.which(cmd) or (cmd if Path(cmd).is_file() else None)
                return None      # a default browser, but not one with --app
        except (OSError, IndexError):
            return None
    return None


def _app_mode_browser():
    """A Chromium-family browser that can open a chrome-less window, if there is one."""
    preferred = _default_browser_binary()
    if preferred:
        return preferred
    for name in APP_MODE_BROWSERS:
        found = shutil.which(name)
        if found:
            return found
    for path in APP_MODE_MACOS + APP_MODE_WINDOWS:
        if Path(path).is_file():
            return path
    return None


def _fresh(url):
    """Handed the same URL twice, a browser focuses the window it already has and
    shows whatever that window last rendered. Launching again after an update
    would then appear to change nothing. A unique query string makes each launch
    a distinct URL, so the page is always fetched anew."""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}t={int(time.time())}"


def open_window(url, prefer_app):
    """Open the page, as an app window when asked for and possible."""
    if prefer_app:
        browser = _app_mode_browser()
        if browser:
            try:
                subprocess.Popen(
                    [browser, f"--app={_fresh(url)}", "--window-size=1180,900"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True)
                return "app window"
            except OSError:
                pass       # fall through to an ordinary tab
    webbrowser.open(_fresh(url))
    return "browser tab"


def already_running(port):
    """True if our own server is already answering on this port.

    Checked before binding so a second launch raises the existing window rather
    than failing on an address clash -- or worse, silently serving a stale copy.
    """
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/data.json",
                                    timeout=1.5) as r:
            json.loads(r.read().decode("utf-8"))
            return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


class SaveReader:
    """Reads the save, and re-reads it only once the file has actually changed.

    The page polls on a timer, so this has to be cheap to call. A stat() is cheap;
    inflating five megabytes of JSON is not.
    """

    def __init__(self, explicit=None):
        self.explicit = explicit
        self.lock = threading.Lock()
        self.cached = None
        self.cached_key = None
        self.error = None

    def current(self, force=False):
        with self.lock:
            try:
                path = nms_save.newest_save(self.explicit)
                key = (str(path), path.stat().st_mtime_ns)
                if force or key != self.cached_key:
                    self.cached = nms_save.build_payload(path)
                    self.cached_key = key
                self.error = None
            except Exception as exc:      # surfaced in the page, not a traceback
                self.error = str(exc)
            return self.cached, self.error


class Handler(BaseHTTPRequestHandler):
    reader = None
    interval = DEFAULT_INTERVAL

    def log_message(self, *args):
        pass                              # a polling page would flood the console

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path in ("/", "/index.html"):
            try:
                html = PAGE.read_bytes()
            except OSError:
                self._send(500, b"index.html is missing from the project folder.",
                           "text/plain; charset=utf-8")
                return
            self._send(200, html, "text/html; charset=utf-8")
            return

        if path == "/data.json":
            force = "force=1" in self.path
            data, error = self.reader.current(force=force)
            payload = {"ok": error is None, "error": error,
                       "interval": self.interval, "data": data}
            self._send(200, json.dumps(payload).encode("utf-8"),
                       "application/json; charset=utf-8")
            return

        self._send(404, b"Not found", "text/plain; charset=utf-8")


def main():
    p = argparse.ArgumentParser(
        description="Rank No Man's Sky teleporter destinations by distance to the "
                    "galactic core.")
    p.add_argument("--save", help="path to a save.hg file, or the folder holding it")
    p.add_argument("--port", type=int, default=DEFAULT_PORT,
                   help=f"port to serve on (default: {DEFAULT_PORT})")
    p.add_argument("--app", action="store_true",
                   help="open as a plain window with no tabs or address bar, "
                        "if a Chromium-family browser is installed")
    p.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                   help=f"seconds between save checks (default: {DEFAULT_INTERVAL})")
    p.add_argument("--no-browser", action="store_true",
                   help="do not open a browser window")
    p.add_argument("--list", action="store_true",
                   help="list every save found on this machine, then exit")
    args = p.parse_args()

    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass

    if args.list:
        saves = nms_save.find_saves()
        if not saves:
            print("No No Man's Sky saves found. See the README for where to look.")
            return 1
        print(f"{len(saves)} save file(s), newest first:\n")
        for s in saves:
            when = time.strftime("%Y-%m-%d %H:%M", time.localtime(s.stat().st_mtime))
            print(f"  {when}   {s}")
        return 0

    # Launched twice -- a second double-click of a desktop shortcut, say -- just
    # show the window that already exists.
    if args.port and already_running(args.port):
        url = f"http://127.0.0.1:{args.port}/"
        print(f"Already running at {url} -- opening that instead of starting again.")
        if not args.no_browser:
            open_window(url, args.app)
        return 0

    reader = SaveReader(args.save)
    data, error = reader.current()
    if error and data is None:
        print(error, file=sys.stderr)
        return 1

    here = data["here"]
    print(f"Save:     {data['path']}")
    print(f"Position: {here['distance_ly']:,} ly from the core, in "
          f"{here['galaxy_name']}")
    print(f"Ranked:   {len(data['eps'])} teleporter destinations")

    Handler.reader = reader
    Handler.interval = max(10, args.interval)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        # Something else holds the port. Take any free one rather than refusing.
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"

    print(f"\nServing at {url}")
    print(f"Checking for a newer save every {Handler.interval} seconds.")
    print("Press Ctrl+C to stop.")

    if not args.no_browser:
        threading.Timer(0.4, lambda: open_window(url, args.app)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
