import sys
import signal
import os
import json
import argparse
import configparser
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
	# read the config file
	config = configparser.ConfigParser()
	config.read(config_file)

	# create logger
	logging.config.fileConfig(config_file)
	# logging.config.fileConfig(config)
	logger = logging.getLogger('acph.main')

	# start ACPH Flights logbook daemon
	logger.warning('ACPH Flights logbook starting with config file = {} (process ID is {}).'.format(config_file,os.getpid()))

	# load the OGN devices database from a local file or remote server
	try:
		if 'logbook' in config and config['logbook']['ognddb'] == 'remote':
			ogndb = OgnDevicesDatabase.withURL()
		else:
			json_filepath = './ogn-devices-ddb.json'
			ogndb = OgnDevicesDatabase.withJsonFile(json_filepath)
	except IOError as err:
		logger.error("Unable to load OGN devices database. Error is {}".format(err))
		sys.exit()

	# load the airport database from a local file for test purpose
	try:
		if 'logbook' in config and config['logbook']['acdb'] == 'remote':
			airports_db = AirportDatabase.withPackageUrl()
		else:
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

	# Create the persistence engine to store results on the fly: could be JSON or MySql
	pdo_engine = FlightLogPDO.factory(config['logbook']['persistence'] if 'logbook' in config else 'JSON')
	# pdo_engine.open(config_file)
	pdo_engine.open(config['mysql_connector_python'])

	# take the opportunity to purge data hold in the persistence engine
	pdo_engine.purge(config['logbook'].getint('purge'))

	# client = AcphAprsClient(aprs_user='ACPH', aprs_passcode='25321')						# Full feed
	# client = AcphAprsClient(aprs_user='ACPH', aprs_passcode='25321', aprs_filter='r/45.5138/3.2661/200')
	if 'aprs' in config:
		client = AcphAprsClient(aprs_user=config['aprs']['user'], aprs_passcode=config['aprs']['passcode'], aprs_filter=config['aprs']['filter'])
	else:
		client = AprsClient(aprs_user='N0CALL')

	client.connect()

	# create the ACPH Flight logbook
	# logbook = FlightsLogBook(receivers_filter={'LFHA', 'LFHP'})
	logbook = FlightsLogBook(receivers_filter=None, ogndb=ogndb, airports_db = listOfAirportsFiltered, pdo_engine = pdo_engine)
	try:
		client.run(callback=logbook.handleBeacon, autoreconnect=True)
	except (KeyboardInterrupt, SystemExit):
		# close the logbook persistent engine
		logbook.pdo_engine.close()

		# close the connection to aprs server.
		client.disconnect()
		
		logger.warning('ACPH Flights logbook stopped...')

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