#!/bin/sh

# Remote
# PY3="python3"
# SCRIPT_TO_LAUNCH="./acph-logbook.py"
# HOME="/kunden/homepages/15/d223327471/htdocs/PyAcphFlightsLog"
# LOGROTATE="/usr/sbin/logrotate"
# LOGROTATE_CONF="$HOME/logrotate.conf"

# Local
PY3="python3"
SCRIPT_TO_LAUNCH="./acph-logbook.py"
HOME=/Users/zazart/Documents/SiteWeb\ ACPH/PyAcphFlightsLog
LOGROTATE="/usr/local/sbin/logrotate"
LOGROTATE_CONF="$HOME/logrotate.conf"

# Stop the running acph logbook python app
# First try to use the pid file
# echo "$HOME/acph-flights-log.pid"
pkill -F "$HOME/acph-flights-log.pid"
pkillexitstatus=$?

# if pkill return an error, check is process is still runing and try to kill it.
if [ ! $pkillexitstatus -eq 0 ] ; then
	ACPH_PID=$(ps aux  | grep '[a]cph-logbook.py' | awk '{print $2}')
	if [ "$ACPH_PID" = "" ] ; then
		echo "No ACPH logbook program running to stop."
	else
		echo "PID to stop is $ACPH_PID"
		kill "$ACPH_PID"
	fi
fi

# rotate the log
cd "$HOME"
"$LOGROTATE" -f -s "$HOME/logrotate.status" "$LOGROTATE_CONF"

# (re)start the program
cd "$HOME"
nohup "$PY3" "$SCRIPT_TO_LAUNCH" > /dev/null 2>&1 &