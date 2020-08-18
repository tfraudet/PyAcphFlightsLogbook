import sys
import signal
import os
import json
import argparse

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
from acph.class_airport_db import AirportDatabase

config_file='./acph-logbook.ini'

def handle_exit(signal, frame):
	raise(SystemExit)
 
@pidfile('acph-flights-log.pid','./')
def main():
	# create logger
	logging.config.fileConfig(config_file)
	logger = logging.getLogger('acph.main')

	# start ACPH APRS logger daemon
	logger.warning('ACPH APRS logger starting with config file = {} (process ID is {}).'.format(config_file,os.getpid()))

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
		airports_db_file = 'airport-codes.json'
		airports_db = AirportDatabase.withJsonFile(airports_db_file)

		#  Airports DB only with european airports.
		# listOfAirportsFiltered = airports_db.filterByContinent('EU')
		# logger.info('After filtering on european airport, size of airport code database is {}'.format(len(listOfAirportsFiltered)))

		# Airports DB only with french airports.
		listOfAirportsFiltered = airports_db.filterByCountry('FR')
		logger.warning('After filtering on French airport, size of airport code database is {}'.format(len(listOfAirportsFiltered)))
	except IOError:
		logger.error("File {} does not exist. Exiting...".format(airports_db_file))
		sys.exit()

	# to handle CTRL-C, Kill,....
	signal.signal(signal.SIGTERM, handle_exit)

	# Create the PDO Engine to store the results on the fly: could be JSON or MySql
	# pdo_engine = FlightLogPDO.factory('JSON')
	pdo_engine = FlightLogPDO.factory('MYSQL')

	# client = AprsClient(aprs_user='N0CALL')
	# client = AcphAprsClient(aprs_user='ACPH', aprs_passcode='25321')						# Full feed
	client = AcphAprsClient(aprs_user='ACPH', aprs_passcode='25321', aprs_filter='r/45.5138/3.2661/200')
	client.connect()

	# create the ACPH Flight logbook
	# logbook = FlightsLogBook(receivers_filter={'LFHA', 'LFHP'})
	logbook = FlightsLogBook(receivers_filter=None, ogndb=ogndb, airports_db = listOfAirportsFiltered, pdo_engine = pdo_engine)

	# open the Logbook persistent engine
	logbook.pdo_engine.open(config_file)

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
		parser = argparse.ArgumentParser(description='ACPH Glider flight logbook daemon')
		parser.add_argument("-i", "--ini", action='store', dest='config_file', help='path to the ini config file, default value is {}'.format(config_file),
							 default='./acph-logbook.ini')
							#  default='./acph-logbook.ini', required=True)
		args = parser.parse_args()
		config_file=args.config_file

		main()
	except pid.PidFileError as error:
		# print(type(error),error, error.args)
		print(type(error),error)