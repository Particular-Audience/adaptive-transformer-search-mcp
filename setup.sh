#!/bin/bash
# Simple setup script using UV

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "UV not found. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Check if installation was successful
    if ! command -v uv &> /dev/null; then
        echo "Failed to install UV. Please install manually from https://github.com/astral-sh/uv"
        exit 1
    fi
fi

echo "Setting up project environment..."

# Install Python 3.11 if needed
echo "Checking/installing Python 3.11..."
uv python install 3.11 --quiet

# Create virtual environment with Python 3.11
echo "Creating virtual environment with Python 3.11..."
uv venv --python 3.11

# Activate virtual environment
source .venv/bin/activate

# Install dependencies directly from project configuration
uv pip install -e .

# Create an empty .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating empty .env file..."
    touch .env
    echo "# Authentication settings
AUTH_ENDPOINT=https://your-auth-endpoint.example.com
SEARCH_API_ENDPOINT=https://your-search-api.example.com
CLIENT_ID=your_client_id_here
CLIENT_SHORTCODE=your_client_shortcode_here
CLIENT_SECRET=your_client_secret_here

# Server settings
HOST=0.0.0.0
PORT=3000
MESSAGE_PATH=/mcp/messages/" > .env
    echo "IMPORTANT: Please edit the .env file with your actual credentials before running the server."
fi

echo "Setup complete! Run the server with: uv run mcp_search_server.py" 