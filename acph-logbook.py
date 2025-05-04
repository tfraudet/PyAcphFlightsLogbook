import sys
import signal
import os
import json
import argparse
import configparser
import logging
import logging.config
from logging.handlers import TimedRotatingFileHandler
import threading

import pid
from pid.decorator import pidfile

from ogn.client import AprsClient
from ogn.parser import parse, ParseError

from acph.class_aprs import AcphAprsClient
from acph.class_flights_logbook import FlightsLogBook
from acph.class_ogn_db import OgnDevicesDatabase
from acph.class_flights_logbook_pdo import FlightLogPDO
from acph.class_airport_db import OurAirportsDatabase
# from api_server import LogbookApiServer  # Import the new API server class

import schedule
import time

def handle_exit(signal, frame):
	raise(SystemExit)

def setup_purge_job(pdo_engine: FlightLogPDO, days: int):
	logger = logging.getLogger('acph.main')
	
	# Do an immediate purge
	logger.warning("Purge scheduler thread: Performing initial database purge...")
	pdo_engine.purge(days)
	
	def purge_scheduler_thread():
		def purge_job():
			logger.warning("Purge scheduler thread: running scheduled purge...")
			pdo_engine.purge(days)
		
		# Schedule the purge job to run daily
		schedule.every().day.at("01:00").do(purge_job)  # Run daily at 1 AM
		# schedule.every(10).seconds.do(purge_job)  # Run every 10 seconds for testing

		while True:
			schedule.run_pending()
			time.sleep(60)  # Check schedule every minute
	
	# Create and start the purge scheduler thread
	purge_thread = threading.Thread(target=purge_scheduler_thread, daemon=True)
	purge_thread.start()
	logger.warning("Purge scheduler thread started")
 
@pidfile('acph-flights-log.pid','./')
def main(config_file = './acph-logbook.ini'):

	# Prepare defaults dictionary including environment variables
	env_defaults = {key.upper(): value for key, value in os.environ.items()}

	# Read config file and create the logger
	config = configparser.ConfigParser(defaults=env_defaults,interpolation=configparser.ExtendedInterpolation())
	config.read(config_file)
	logging.config.fileConfig(config)
	logger = logging.getLogger('acph.main')

	# start ACPH Flights logbook daemon
	logger.critical('ACPH Flights logbook - Main version v2025.1')
	logger.warning('ACPH Flights logbook - Main starting with config file = {} (process ID is {}).'.format(config_file,os.getpid()))

	logger.info('Database connection parameters are: user={}, password={}, database={}, host={}, port={}'.format(
			config['database']['user'],
			config['database']['password'],
			config['database']['database'], 
			config['database']['host'], 
			config['database']['port']))
	
	logger.info('SLACK_WEBHOOK_URL is: {}'.format(config['handler_slackHandler']['args']))

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

	# load the airport database from a local file or remotly
	try:
		if 'logbook' in config and config['logbook']['acdb'] == 'remote':
			airports_db = OurAirportsDatabase.withUrl()
		else:
			airports_db = OurAirportsDatabase.withCsvFile('.')

		#  Airports DB only with european airports.
		# listOfAirportsFiltered = airports_db.filterByContinent('EU')
		# logger.info('After filtering on european airport, size of airport code database is {}'.format(len(listOfAirportsFiltered)))

		# Airports DB only with french airports.
		listOfAirportsFiltered = airports_db.filterByCountry('FR')
		logger.warning('After filtering on French airport, size of airport code database is {}'.format(len(listOfAirportsFiltered)))
	except IOError:
		logger.exception("File does not exist. Exiting...")
		sys.exit()

	# to handle CTRL-C, Kill,....
	signal.signal(signal.SIGTERM, handle_exit)

	# Create the persistence engine to store results on the fly: could be JSON or MySql
	pdo_engine = FlightLogPDO.factory(config['logbook']['persistence'] if 'logbook' in config else 'JSON')
	# pdo_engine.open(config_file)
	pdo_engine.open(config['database'])

	# take the opportunity to purge data hold in the persistence engine
	setup_purge_job(pdo_engine, config['logbook'].getint('purge'))
	
	# Initialize and start the REST API server
	# api_port = int(config['api']['port']) if 'api' in config and 'port' in config['api'] else 5000
	# api_host = config['api']['host'] if 'api' in config and 'host' in config['api'] else '0.0.0.0'
	# api_server = LogbookApiServer(pdo_engine, host=api_host, port=api_port)
	# api_server.start()

	# start the APRS client
	if 'aprs' in config:
		# client = AcphAprsClient(aprs_user=config['aprs']['user'], aprs_passcode=config['aprs']['passcode'], aprs_filter=config['aprs']['filter'])
		# client = AprsClient(aprs_user=config['aprs']['user'], aprs_filter=config['aprs']['filter'])
		client = AprsClient(aprs_user='N0CALL', aprs_filter=config['aprs']['filter'])
	else:
		client = AprsClient(aprs_user='N0CALL')
	client.connect()

	# create the ACPH Flight logbook
	logbook = FlightsLogBook(receivers_filter={'NAVITER'}, ogndb=ogndb, airports_db = listOfAirportsFiltered, pdo_engine = pdo_engine)
	try:
		client.run(callback=logbook.handleBeacon, autoreconnect=True)
	except (KeyboardInterrupt, SystemExit):
		# Stop the API server
		# logger.warning("Stopping API server...")
		# api_server.stop()
		
		# close the logbook persistent engine
		logger.warning("Closing database connection...")
		logbook.pdo_engine.close()

		# close the connection to aprs server.
		logger.warning("Disconnecting from APRS server...")
		client.disconnect()
		
		logger.warning('ACPH Flights logbook stopped...')
	except Exception as e:
		# Stop the API server
		# api_server.stop()
		logger.exception('ACPH Flights logbook stopped with error: {}'.format(e))

if __name__ == '__main__':
	try:
		parser = argparse.ArgumentParser(description='ACPH Glider flight logbook daemon')
		parser.add_argument("-i", "--ini", action='store', dest='config_file', help='path to the ini config file',
							 default='./acph-logbook.ini')
							#  default='./acph-logbook.ini', required=True)
		args = parser.parse_args()
		config_file=args.config_file

		main(config_file)
	except pid.PidFileError as error:
		# print(type(error),error, error.args)
		print(type(error),error)