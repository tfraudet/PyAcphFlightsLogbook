#!/bin/sh

# Remote
# PY3="python3"
# SCRIPT_TO_LAUNCH="./acph-logbook.py"
# HOME="/kunden/homepages/15/d223327471/htdocs/PyAcphFlightsLog"

# Local
PY3="python3"
SCRIPT_TO_LAUNCH="./acph-logbook.py"
HOME=/Users/zazart/Documents/SiteWeb\ ACPH/PyAcphFlightsLog

# Syntax to run php script in backgroud
# nohup exec arg1 arg2 > /dev/null &
# Use & to execute a command (or shell script) as a background job 
# Use nohup to avoid the job get killed after logout the session
# Redirect the stdout and stderr to /dev/null to ignore the output.

cd "$HOME"
nohup "$PY3" "$SCRIPT_TO_LAUNCH" > /dev/null 2>&1 &