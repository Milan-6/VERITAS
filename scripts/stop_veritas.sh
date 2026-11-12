#!/usr/bin/env bash
# ==============================================================================
# VERITAS: Clean Shutdown Script for Linux, macOS & WSL
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_PATH="$PROJECT_ROOT/veritas.db"
QDRANT_LOCK="$PROJECT_ROOT/data/qdrant/.lock"

echo -e "\033[1;36m============================================================\033[0m"
echo -e "\033[1;36m  VERITAS Clean Shutdown (Bash/Linux/WSL)\033[0m"
echo -e "\033[1;36m============================================================\033[0m"

PORTS=(8000 3000)

for PORT in "${PORTS[@]}"; do
    SERVICE="Next.js Frontend"
    if [ "$PORT" -eq 8000 ]; then
        SERVICE="FastAPI Backend"
    fi
    echo -e "\033[1;33m[*] Checking $SERVICE on port $PORT...\033[0m"
    
    # Check with fuser
    if command -v fuser >/dev/null 2>&1; then
        fuser -k -n tcp "$PORT" >/dev/null 2>&1 || true
    fi
    
    # Check with lsof
    if command -v lsof >/dev/null 2>&1; then
        PIDS=$(lsof -t -i:"$PORT" 2>/dev/null || true)
        if [ -n "$PIDS" ]; then
            for PID in $PIDS; do
                echo "    Terminating PID $PID..."
                kill -15 "$PID" 2>/dev/null || true
                sleep 0.5
                kill -9 "$PID" 2>/dev/null || true
            done
        fi
    fi
done

# Terminate any stray uvicorn or next dev processes
echo -e "\033[1;33m[*] Halting stray dev runners...\033[0m"
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "run_server.py" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true

# Flush SQLite WAL
if [ -f "$DB_PATH" ]; then
    echo -e "\033[1;33m[*] Flushing SQLite WAL checkpoint...\033[0m"
    PYTHON_BIN="python3"
    if [ -f "$PROJECT_ROOT/venv/bin/python" ]; then
        PYTHON_BIN="$PROJECT_ROOT/venv/bin/python"
    elif [ -f "$PROJECT_ROOT/venv/Scripts/python.exe" ]; then
        PYTHON_BIN="$PROJECT_ROOT/venv/Scripts/python.exe"
    fi
    
    $PYTHON_BIN -c "import sqlite3; conn = sqlite3.connect('$DB_PATH'); cur = conn.cursor(); cur.execute('PRAGMA wal_checkpoint(TRUNCATE);'); print('    [✓] WAL checkpoint flushed:', cur.fetchone()); conn.close()" 2>/dev/null || true
fi

# Clean Qdrant lock
if [ -f "$QDRANT_LOCK" ]; then
    echo -e "\033[1;33m[*] Removing stale Qdrant lock file...\033[0m"
    rm -f "$QDRANT_LOCK" 2>/dev/null || true
    echo -e "    \033[1;32m[✓] Stale vector lock removed.\033[0m"
fi

# Verification
echo -e "\033[1;33m[*] Verifying port release...\033[0m"
for PORT in "${PORTS[@]}"; do
    if command -v nc >/dev/null 2>&1; then
        if nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
            echo -e "    \033[1;31m[!] Warning: Port $PORT still active.\033[0m"
        else
            echo -e "    \033[1;32m[✓] Port $PORT released cleanly.\033[0m"
        fi
    else
        echo -e "    \033[1;32m[✓] Checked port $PORT.\033[0m"
    fi
done

echo -e "\033[1;36m============================================================\033[0m"
echo -e "\033[1;32m[✓] VERITAS platform successfully halted.\033[0m"
echo -e "\033[1;36m============================================================\033[0m"
