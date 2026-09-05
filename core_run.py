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
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import nms_save

HERE = Path(__file__).resolve().parent
PAGE = HERE / "index.html"
DEFAULT_INTERVAL = 120


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
    p.add_argument("--port", type=int, default=0,
                   help="port to serve on (default: pick a free one)")
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
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"

    print(f"\nServing at {url}")
    print(f"Checking for a newer save every {Handler.interval} seconds.")
    print("Press Ctrl+C to stop.")

    if not args.no_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
