#!/bin/bash

# Saga Express - Stop Script
# This script stops the Saga Express application and related processes

set -e  # Exit on any error

echo " Stopping Saga Express..."

# Function to find and kill processes by name
kill_process() {
    local process_name=$1
    local pids=$(pgrep -f "$process_name" 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        echo " Found $process_name processes: $pids"
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        sleep 2
        
        # Check if processes are still running and force kill if necessary
        local remaining_pids=$(pgrep -f "$process_name" 2>/dev/null || true)
        if [ -n "$remaining_pids" ]; then
            echo "  Force killing remaining $process_name processes: $remaining_pids"
            echo "$remaining_pids" | xargs kill -KILL 2>/dev/null || true
        fi
        echo " Stopped $process_name"
    else
        echo "  No $process_name processes found"
    fi
}

# Stop uvicorn processes (main application)
kill_process "uvicorn app.main:app"

# Stop any remaining Python processes related to saga-express
kill_process "python.*saga"

# Stop mock services if running
echo " Stopping mock services..."
kill_process "python.*mock_services"
kill_process "python.*order_service"
kill_process "python.*inventory_service"
kill_process "python.*payment_service"

# Stop any processes using port 8000 (main app)
echo " Checking for processes using port 8000..."
port_8000_pid=$(lsof -ti:8000 2>/dev/null || true)
if [ -n "$port_8000_pid" ]; then
    echo " Found process using port 8000: $port_8000_pid"
    kill -TERM $port_8000_pid 2>/dev/null || true
    sleep 2
    # Force kill if still running
    if kill -0 $port_8000_pid 2>/dev/null; then
        kill -KILL $port_8000_pid 2>/dev/null || true
    fi
    echo " Stopped process on port 8000"
else
    echo "  No process found using port 8000"
fi

# Stop processes on mock service ports (8001, 8002, 8003)
for port in 8001 8002 8003; do
    echo " Checking for processes using port $port..."
    port_pid=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$port_pid" ]; then
        echo " Found process using port $port: $port_pid"
        kill -TERM $port_pid 2>/dev/null || true
        sleep 1
        # Force kill if still running
        if kill -0 $port_pid 2>/dev/null; then
            kill -KILL $port_pid 2>/dev/null || true
        fi
        echo " Stopped process on port $port"
    else
        echo "  No process found using port $port"
    fi
done

echo ""
echo " Saga Express has been stopped successfully!"
echo " To start again, run: ./run.sh"
echo ""