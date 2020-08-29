#!/bin/sh

# Remote
# PY3="/usr/bin/python3"
# LOGROTATE="/usr/sbin/logrotate"
# HOME_LOGBOOK="$HOME/PyAcphFlightsLog"

# Local
PY3="python3"
LOGROTATE="/usr/local/sbin/logrotate"
HOME_LOGBOOK="$HOME/Documents/SiteWeb ACPH/PyAcphFlightsLog"

SCRIPT_TO_LAUNCH="$HOME_LOGBOOK/acph-logbook.py"
LOGROTATE_CONF="$HOME_LOGBOOK/logrotate.conf"

# Stop the running acph logbook python app
# First try to use the pid file
# echo "HOME_LOGBOOK/acph-flights-log.pid"
echo "Stop the running ACPH logbook app"
pkill -F "$HOME_LOGBOOK/acph-flights-log.pid"
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
echo "Rotate the logp"
cd "$HOME_LOGBOOK"
"$LOGROTATE" -f -s "$HOME_LOGBOOK/logrotate.status" "$LOGROTATE_CONF"

# (re)start the program
echo "Restart the ACPH logbook app"
cd "$HOME_LOGBOOK"
# Sleep for 1minute as workaround for the following error
# <class 'pid.base.PidFileAlreadyLockedError'> [Errno 11] Resource temporarily unavailable
sleep 1m
"$PY3" "$SCRIPT_TO_LAUNCH" &