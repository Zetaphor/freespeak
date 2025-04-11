#!/bin/bash

# Get the absolute path to the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script directory
cd "$SCRIPT_DIR"

# Check if the virtual environment exists
# Use the full path in the check and error message
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
  echo "Error: Virtual environment '$SCRIPT_DIR/.venv' not found"
  exit 1
fi

# Activate the virtual environment using the full path
source "$SCRIPT_DIR/.venv/bin/activate"

# Check if the Python file exists using the full path
if [ ! -f "$SCRIPT_DIR/src/main.py" ]; then
  echo "Error: Python script '$SCRIPT_DIR/src/main.py' not found"
  exit 1
fi

# Run the Flask application using the full path
python "$SCRIPT_DIR/src/main.py" > /dev/null 2>&1 &

# Print a success message with the PID
echo "Flask application started in background with PID $!"
