#!/bin/bash
# Convenient wrapper for generate_figures.py
# Usage: ./run_analysis.sh Slope2D093 "-55 -45 -35"

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <runname> \"<mooringX values>\""
    echo "Example: $0 Slope2D093 \"-55 -45 -35\""
    exit 1
fi

RUNNAME=$1
MOORINGS=$2

echo "Running analysis for ${RUNNAME} with moorings: ${MOORINGS}"
python generate_figures.py --runname ${RUNNAME} --mooringX ${MOORINGS}
