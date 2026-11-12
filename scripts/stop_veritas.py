#!/usr/bin/env python3
"""
VERITAS Clean Shutdown & Process Lifecycle Management Utility.
Safely terminates VERITAS backend (port 8000), frontend (port 3000),
flushes SQLite WAL checkpoint, and removes stale vector store locks.
Works across Windows, Linux, and macOS.
"""

import os
import sys
import time
import signal
import socket
import sqlite3
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "veritas.db"
QDRANT_LOCK = PROJECT_ROOT / "data" / "qdrant" / ".lock"

PORTS_TO_CLEAR = [8000, 3000]


def print_step(msg: str):
    print(f"\033[94m[*] {msg}\033[0m")


def print_success(msg: str):
    print(f"\033[92m[✓] {msg}\033[0m")


def print_warning(msg: str):
    print(f"\033[93m[!] {msg}\033[0m")


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def get_pids_for_port(port: int) -> list[int]:
    pids = []
    if os.name == "nt":
        # Windows: parse netstat output
        try:
            output = subprocess.check_output(
                f'netstat -ano | findstr :{port}', shell=True, text=True, stderr=subprocess.DEVNULL
            )
            for line in output.strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[3] == "LISTENING":
                    try:
                        pid = int(parts[4])
                        if pid > 0 and pid not in pids:
                            pids.append(pid)
                    except ValueError:
                        continue
                elif len(parts) >= 4 and not parts[3].isdigit():
                    try:
                        pid = int(parts[-1])
                        if pid > 0 and pid not in pids:
                            pids.append(pid)
                    except ValueError:
                        continue
        except subprocess.CalledProcessError:
            pass
    else:
        # Linux / macOS: use lsof or fuser
        try:
            output = subprocess.check_output(
                f"lsof -t -i:{port}", shell=True, text=True, stderr=subprocess.DEVNULL
            )
            for line in output.strip().splitlines():
                if line.strip().isdigit():
                    pids.append(int(line.strip()))
        except subprocess.CalledProcessError:
            pass
    return pids


def terminate_pid(pid: int):
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            # If still alive, force kill
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        print_success(f"Terminated process PID {pid}")
    except Exception as e:
        print_warning(f"Failed to terminate PID {pid}: {e}")


def terminate_by_process_names():
    patterns = ["uvicorn", "next-server"]
    print_step("Scanning for lingering VERITAS processes...")
    if os.name == "nt":
        # Windows tasklist / taskkill
        try:
            # Check python processes running run_server.py
            output = subprocess.check_output(
                'wmic process where "caption=\'python.exe\'" get processid,commandline',
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL,
            )
            for line in output.splitlines():
                if "run_server.py" in line or "app.main:app" in line:
                    parts = line.strip().split()
                    if parts and parts[-1].isdigit():
                        pid = int(parts[-1])
                        print_step(f"Found VERITAS Python process PID {pid}")
                        terminate_pid(pid)
        except Exception:
            pass
    else:
        # Linux / macOS pkill
        for pat in patterns:
            try:
                subprocess.run(f"pkill -f {pat}", shell=True, stderr=subprocess.DEVNULL)
            except Exception:
                pass


def flush_sqlite_wal(db_path: Path):
    if not db_path.exists():
        print_warning(f"Database file not found at {db_path}; skipping WAL flush.")
        return

    print_step(f"Flushing SQLite WAL checkpoint on {db_path.name}...")
    try:
        conn = sqlite3.connect(str(db_path), timeout=10.0)
        cursor = conn.cursor()
        # TRUNCATE checkpoint flushes all pages to the database file and shrinks wal file
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        res = cursor.fetchone()
        conn.commit()
        conn.close()
        print_success(f"SQLite WAL checkpoint complete (busy={res[0]}, log={res[1]}, checkpointed={res[2]}).")
    except Exception as e:
        print_warning(f"WAL checkpoint warning: {e}")


def cleanup_vector_locks(lock_path: Path):
    if lock_path.exists():
        print_step(f"Removing stale vector lock {lock_path}...")
        try:
            lock_path.unlink(missing_ok=True)
            print_success("Stale vector lock cleared.")
        except Exception as e:
            print_warning(f"Failed to remove vector lock: {e}")
    else:
        print_success("No stale vector lock found.")


def main():
    print("=" * 60)
    print("  VERITAS System Clean Shutdown & Lifecycle Management")
    print("=" * 60)

    # 1. Check and stop services by ports
    for port in PORTS_TO_CLEAR:
        service_name = "FastAPI Backend" if port == 8000 else "Next.js Frontend"
        print_step(f"Checking {service_name} on port {port}...")
        pids = get_pids_for_port(port)
        if pids:
            print_step(f"Found active PIDs on port {port}: {pids}")
            for pid in pids:
                terminate_pid(pid)
        else:
            print_success(f"Port {port} ({service_name}) is already free.")

    # 2. Terminate any stray runner processes
    terminate_by_process_names()

    # 3. Wait briefly for OS socket release
    time.sleep(1.0)

    # 4. Flush SQLite WAL to ensure zero data loss / corruption
    flush_sqlite_wal(DB_PATH)

    # 5. Clean up Qdrant locks
    cleanup_vector_locks(QDRANT_LOCK)

    # 6. Final port verification
    print_step("Performing final port verification...")
    all_clear = True
    for port in PORTS_TO_CLEAR:
        if is_port_in_use(port):
            print_warning(f"Port {port} is still reporting active socket.")
            all_clear = False
        else:
            print_success(f"Port {port} confirmed clean and released.")

    print("=" * 60)
    if all_clear:
        print("\033[92m[✓] All VERITAS services cleanly stopped and locks released.\033[0m")
    else:
        print("\033[93m[!] VERITAS stopped with warnings on active sockets.\033[0m")
    print("=" * 60)


if __name__ == "__main__":
    main()
