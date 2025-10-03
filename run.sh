#!/bin/bash

# Saga Express - Run Script
# This script sets up and starts the Saga Express application

set -e  # Exit on any error

echo " Starting Saga Express setup..."

# Check if we're in the correct directory
if [ ! -f "pyproject.toml" ]; then
    echo " Error: pyproject.toml not found. Please run this script from the saga-express directory."
    exit 1
fi

# Navigate to saga-express directory (in case script is run from parent)
cd "$(dirname "$0")"

echo " Current directory: $(pwd)"

# Create virtual environment with uv
echo " Creating virtual environment with uv..."
if ! command -v uv &> /dev/null; then
    echo " Error: uv is not installed. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if virtual environment already exists
if [ -d ".venv" ]; then
    echo " Virtual environment already exists. Continuing with existing environment..."
else
    uv venv
fi

# Activate virtual environment
echo " Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo " Installing dependencies..."
uv pip install -e .

# Check if .env file exists, if not copy from example
if [ ! -f ".env" ]; then
    echo "  Creating .env file from .env.example..."
    cp .env.example .env
    echo " .env file created. Please review and update if needed."
else
    echo " .env file already exists."
fi

# Run database migrations
echo "  Running database migrations..."
if ! command -v alembic &> /dev/null; then
    echo " Error: alembic not found in virtual environment"
    exit 1
fi

alembic upgrade head

# Start the application
echo " Starting Saga Express application..."
echo " Application will be available at: http://localhost:8000"
echo " API documentation at: http://localhost:8000/docs"
echo " Health check at: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000