"""Local launcher; a bootstrap secret is delivered only in a browser fragment."""
from __future__ import annotations

import argparse
import http.client
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def wait_ready(host: str, port: int, path: str, processes: list[subprocess.Popen]) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if any(process.poll() is not None for process in processes):
            raise RuntimeError("Local service exited before startup completed")
        connection = http.client.HTTPConnection(host, port, timeout=1)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            response.read()
            if response.status == 200:
                return
        except OSError:
            pass
        finally:
            connection.close()
        time.sleep(0.1)
    raise RuntimeError("Local service did not become ready within 30 seconds")


def launch(mode: str, open_browser: bool) -> None:
    from services.api.app.config import Settings
    from services.api.app.database import Database
    from services.api.app.security import issue_bootstrap_code

    environment = dict(os.environ)
    if mode == "dev":
        environment["LEARNING_UI_ORIGIN"] = "http://127.0.0.1:5173"
        os.environ["LEARNING_UI_ORIGIN"] = environment["LEARNING_UI_ORIGIN"]
    settings = Settings.from_env()
    database = Database(settings)
    database.initialize()
    code = issue_bootstrap_code(database)
    port = settings.port
    if mode == "start" and not (ROOT / "apps/web/dist/index.html").exists():
        raise SystemExit("Production build missing; run make build before make start.")
    processes: list[subprocess.Popen] = []

    def stop(*_args) -> None:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()

    def on_signal(*_args) -> None:
        raise KeyboardInterrupt()

    signal.signal(signal.SIGTERM, on_signal)
    try:
        processes.append(subprocess.Popen([
            sys.executable, "-m", "uvicorn", "services.api.app.main:create_app", "--factory", "--host", settings.host,
            "--port", str(port), "--no-access-log"], cwd=ROOT, env=environment))
        if mode == "dev":
            processes.append(subprocess.Popen(["bash", "scripts/node.sh", "npm", "--prefix", "apps/web", "run", "dev"],
                                              cwd=ROOT, env=environment))
        base = "http://127.0.0.1:5173" if mode == "dev" else settings.origin
        wait_ready(settings.host, port, "/health", processes)
        wait_ready("127.0.0.1" if mode == "dev" else settings.host, 5173 if mode == "dev" else port, "/", processes)
        # No query parameter or access log contains the code. The terminal is local,
        # and the launch URL must never be copied into a diagnostic/public receipt.
        if open_browser:
            webbrowser.open(base + "/#bootstrap=" + code)
            print(f"Opened local workbench at {base}; one-time bootstrap sent in browser fragment.", flush=True)
        else:
            print("Local launch URL (private, expires after use): " + base + "/#bootstrap=" + code, flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.3)
        failed = [process.returncode for process in processes if process.returncode not in (None, 0)]
        if failed:
            raise SystemExit(f"Local service exited: {failed}")
    except KeyboardInterrupt:
        pass
    finally:
        stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["dev", "start"])
    parser.add_argument("--no-browser", action="store_true")
    arguments = parser.parse_args()
    launch(arguments.mode, not arguments.no_browser)
