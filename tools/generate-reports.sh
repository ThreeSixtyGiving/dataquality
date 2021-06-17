#!/bin/bash
# Note these python scripts all assume './data/' dir
set -e
echo 'Generating status.json'
aggregates.py
echo 'Generating coverage.json'
coverage360.py
echo 'Generating report.csv'
report.py
echo 'Finished'
