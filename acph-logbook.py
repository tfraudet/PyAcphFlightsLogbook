import sys
import signal
import os
import json

import logging
import logging.config
from logging.handlers import TimedRotatingFileHandler

import pid
from pid.decorator import pidfile

from ogn.client import AprsClient
from ogn.parser import parse, ParseError

from acph.class_aprs import AcphAprsClient
from acph.class_flights_logbook import FlightsLogBook
from acph.class_ogn_db import OgnDevicesDatabase
from acph.class_flights_logbook_pdo import FlightLogPDO

def handle_exit(signal, frame):
	raise(SystemExit)
 
@pidfile('acph-flights-log.pid','./')
def main():
	# create logger
	logging.config.fileConfig('acph-logbook.ini')
	logger = logging.getLogger('acph.main')

	# start ACPH APRS logger daemon
	logger.warning('ACPH APRS logger starting (process id is {}).'.format(os.getpid()))

	# load the OGN devices database from a local file for test purpose
	try:
		json_filepath = './ogn-devices-ddb.json'
		ogndb = OgnDevicesDatabase.withJsonFile(json_filepath)
		# ogndb = OgnDevicesDatabase.withURL()
		# ogndb.getAircraftById('DD8E99')
	except IOError:
		logger.error("File {} does not exist. Exiting...".format(json_filepath))
		sys.exit()

	# load the airport database from a local file for test purpose
	try:
		airports_db_file = 'airports.json'
		with open(airports_db_file) as airports_json_file:
			airports = json.load(airports_json_file)
	except IOError:
		logger.error("File {} does not exist. Exiting...".format(airports_db_file))
		sys.exit()

	# to handle CTRL-C, Kill,....
	signal.signal(signal.SIGTERM, handle_exit)

	# Create the PDO Engine to store the results on the fly: could be JSON or MySql
	# pdo_engine = FlightLogPDO.factory('JSON')
	pdo_engine = FlightLogPDO.factory('MYSQL')

	# client = AprsClient(aprs_user='N0CALL')
	# client = AprsClient(aprs_user='ACPH', aprs_filter='r/45.5138/3.2661/200')
	client = AcphAprsClient(aprs_user='ACPH', aprs_passcode='25321', aprs_filter='r/45.5138/3.2661/200')
	client.connect()

	# create the ACPH Flight logbook
	# logbook = FlightsLogBook(airports_icao={'LFHA', 'LFHP'})
	logbook = FlightsLogBook(airports_icao={'LFHA'}, ogndb=ogndb, pdo_engine = pdo_engine)

	# logbook.airports = {k: v for k, v in airports.items() if k in {'LFHA', 'LFHR', 'LFHT', 'LFHP'}}		# filter only some french airports for test purpose
	logbook.airports = {k: v for k, v in airports.items() if k in {'LFHA'}}		# filter only some french airports for test purpose

	# open the Logbook persistent engine
	logbook.pdo_engine.open()

	try:
		client.run(callback=logbook.handleBeacon, autoreconnect=True)
	except (KeyboardInterrupt, SystemExit):
		logger.warning('ACPH APRS logger stopped...')
		
		# close the logbook persistent engine
		logbook.pdo_engine.close()

		# close the connection to aprs server.
		client.disconnect()

if __name__ == '__main__':
	try:
		main()
	except pid.PidFileError as error:
		# print(type(error),error, error.args)
		print(type(error),error)