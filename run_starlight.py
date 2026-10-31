import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def available_port(start: int, end: int) -> int | None:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
        return port
    return None


def wait_for_backend(process: subprocess.Popen, port: int) -> bool:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                if response.status == 200:
                    return True
        except OSError:
            time.sleep(0.25)
    return False


def main() -> int:
    node = shutil.which("node")
    if not node:
        print("npm was not found. Install Node.js 18+ and run `npm install` in frontend.")
        return 1
    if not (FRONTEND / "node_modules").exists():
        print("Frontend dependencies are missing. Run `npm install` in frontend first.")
        return 1

    backend_port = available_port(8000, 8010)
    frontend_port = available_port(5173, 5183)
    if backend_port is None or frontend_port is None:
        print("No free local port is available for StarlightAI.")
        return 1

    processes = []
    try:
        print("Starting StarlightAI services...")
        backend_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(backend_port),
            ],
            cwd=BACKEND,
        )
        processes.append(backend_process)
        if not wait_for_backend(backend_process, backend_port):
            print("The API failed to become ready. Check Python dependencies and local port permissions.")
            return 1

        frontend_env = os.environ.copy()
        frontend_env["STARLIGHT_API_URL"] = f"http://127.0.0.1:{backend_port}"
        processes.append(
            subprocess.Popen(
                [
                    node,
                    str(FRONTEND / "node_modules" / "vite" / "bin" / "vite.js"),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(frontend_port),
                    "--strictPort",
                ],
                cwd=FRONTEND,
                env=frontend_env,
            )
        )
        print(f"Dashboard: http://127.0.0.1:{frontend_port}")
        print(f"Backend API: http://127.0.0.1:{backend_port}")
        print(f"API docs: http://127.0.0.1:{backend_port}/docs")
        print("Press Ctrl+C to stop both services.")
        while True:
            for process in processes:
                exit_code = process.poll()
                if exit_code is not None:
                    return exit_code or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping StarlightAI...")
        return 0
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
