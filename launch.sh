#!/bin/bash

source venv/bin/activate
# Run the Flask application in the background and discard output
python src/main.py > /dev/null 2>&1 &
