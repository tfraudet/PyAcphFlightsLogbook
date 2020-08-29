#!/bin/bash
# set -x #echo on

PRG_NAME="ACPH supervisor 1.0"
CZ=$(date +%H%M)

# Remote
PY3="/usr/bin/python3"
HOME_LOGBOOK="$HOME/PyAcphFlightsLog"
SCRIPT_TO_LAUNCH="$HOME_LOGBOOK/acph-logbook.py"

# Local
# PY3="python3"
# HOME_LOGBOOK="$HOME/Documents/SiteWeb ACPH/PyAcphFlightsLog"
# SCRIPT_TO_LAUNCH="$HOME_LOGBOOK/acph-logbook.py"

if [[ $CZ < 2200 && $CZ > 0700 ]]; then
	echo "$PRG_NAME - Inside time slot, try to restart the logbook python program if it's not running"

	PID_FILE="$HOME_LOGBOOK/acph-flights-log.pid"
	[ -f "$PID_FILE" ] && read PID_FROM_FILE <"$PID_FILE" || PID_FROM_FILE=""
	PID_FROM_PS=$(ps aux  | grep '[a]cph-logbook.py' | awk '{print $2}')
	echo "Process to look for is: PID from file = $PID_FROM_FILE, PID from ps = $PID_FROM_PS"

	# if [[ -z "$PID_FROM_FILE" && -z "$PID_FROM_PS" ]]; then
	if [[ -z "$PID_FROM_PS" ]]; then
		MSG=$([ -z "$PID_FROM_FILE" ] && echo '(and no PID file)' || echo "(nevertheless PID file still exist and PID is $PID_FROM_FILE)")
		echo "Unable to find logbook process from ps command $MSG, we have to restart acph logbook"
		cd "$HOME_LOGBOOK"

		# notify the slack channel
		TIMESTAMP=$(date +"%s")
		printf -v json_payload '{"attachments": [{"ts": "%s","author_name": "CRITICAL", "title": "ACPH supervisor 1.0", "color": "danger","text":"Supervisor detect that the logbook process is no more running, try to restart it."}],}' $TIMESTAMP
		curl -X POST -H 'Content-type: application/json' --data "$json_payload" https://hooks.slack.com/services/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

		# restart the dameon.
		"$PY3" "$SCRIPT_TO_LAUNCH" &
	else
		echo "Logbook process is still running, nothing to do."
	fi
else
	echo "$PRG_NAME - outside time slot, do nothing"
fi