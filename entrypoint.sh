#!/bin/bash

# Launch flights logbook process
# python acph-logbook.py -i ./acph-logbook-local.ini &
python acph-logbook.py -i $LOGBOOK_CONFIG_FILE &

# Launch REST API serveur with 2 workers on port 8000	
gunicorn --bind='0.0.0.0:8000' -w 2 'api_server:app' &

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
# exit $?

echo 'Process ended. keep container alive is: '$KEEP_CONTAINER_ALIVE

if [ "$KEEP_CONTAINER_ALIVE" == "0" ]
then
	echo 'Keeping container alive...';
	while :; do sleep 1; done
fi

echo "Container will be stopped"