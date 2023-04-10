import sys
import os
import re
import json
import time
import datetime
import configparser

from datetime import timedelta
import logging
import logging.config
import logging.handlers

from acph.class_aprs import AcphAprsClient
from acph.class_flights_logbook import FlightsLogBook
from acph.class_ogn_db import OgnDevicesDatabase
from acph.class_flights_logbook_pdo import FlightLogPDO
from acph.class_airport_db import OurAirportsDatabase
from acph.class_flights_logbook import FlightsLogBook

def main():
	filepath = sys.argv[1]
	date_of_data = filepath[len(filepath)-14:len(filepath)-4]

	config_file='./unit-test.ini'
	# read the config file
	config = configparser.ConfigParser()
	config.read(config_file)

	# create logger fo the main
	# logging.config.fileConfig(config_file)
	logging.config.fileConfig(config)
	logger = logging.getLogger('acph.main')

	# load the OGN devices database
	try:
		if 'logbook' in config and config['logbook']['ognddb'] == 'remote':
			ogndb = OgnDevicesDatabase.withURL()
		else:
			json_filepath = './ogn-devices-ddb.json'
			ogndb = OgnDevicesDatabase.withJsonFile(json_filepath)
	except IOError:
		logger.error("File {} does not exist. Exiting...".format(json_filepath))
		sys.exit()

	# load the airport database 
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
		logger.error("File {} does not exist. Exiting...".format(airports_db))
		sys.exit()

	# test if file that content aprs messages exist
	if not os.path.isfile(filepath):
		logger.error("File path {} does not exist. Exiting...".format(filepath))
		sys.exit()

	# Create the PDO Engine to store the results on the fly: could be JSON or MySql
	pdo_engine = FlightLogPDO.factory(config['logbook']['persistence'] if 'logbook' in config else 'JSON')
	pdo_engine.open(config['mysql_connector_python'])

	# take the opportunity to purge data hold in the persistence engine
	pdo_engine.purge(config['logbook'].getint('purge'))

	# create the ACPH Flight logbook and build the logbook for LFHA
	# logbook = FlightsLogBook(receivers_filter={'LFHA','LFHP'}, ogndb = ogndb, airports_db = listOfAirportsFiltered, pdo_engine = pdo_engine)

	# create the ACPH Flight logbook and handling all the beacons received
	logbook = FlightsLogBook(receivers_filter={'NAVITER'}, ogndb = ogndb, airports_db = listOfAirportsFiltered, pdo_engine = pdo_engine)

	# logbook.airports = {k: v for k, v in airports.items() if k in {'LFHA', 'LFHR', 'LFHT', 'LFHP'}}		# filter only some french airports for test purpose
	# logbook.airports = {k: v for k, v in airports.items() if k in {'LFHA'}}		# filter only some french airports for test purpose

	# build the reg-ex to extract raw data from the log
	# aprs_reg = re.compile(r'raw data:\s(.*)')
	# aprs_reg = re.compile(r'\[(\d{4})-(\d{2})-(\d{2})\s(\d{2}):(\d{2}):(\d{2}),(\d*)\].*raw data:\s(.*)')
	aprs_reg = re.compile(r'\[(\d{4})-(\d{2})-(\d{2})\s(\d{2}):(\d{2}):(\d{2}),(\d*)\].*(raw data:|aprs beacon)\s(.*)')

	# and run FlightsLogBook with that data, results are in xxxx
	logger.info('Start to parse the file {}, date of the data is {}'.format(filepath,date_of_data))
	max_line_to_process = -1		# -1 for all
	start_time = time.process_time()
	with open(filepath) as fp:
		numberOfLine = 0
		for line in fp:
			try:
				# if max line reached, stop processing
				if  max_line_to_process>0 and numberOfLine >= max_line_to_process:
					break

				# processing next line
				matches = aprs_reg.finditer(line)

				# matches has 0 or 1 element
				for match in matches:
					# logger.info("line {}, processing data: {}".format(numberOfLine, line))
					beacon_timestamp = datetime.datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4)), int(match.group(5)), int(match.group(6)), int(match.group(7)))
					logbook.handleBeacon(match.group(9), beacon_timestamp, date_of_data)
					numberOfLine += 1

				# aprs_raw_data = aprs_reg.findall(line)
				# if len(aprs_raw_data) == 1:
				# 	logbook.handleBeacon(aprs_raw_data[0],  date_of_data)
			except (KeyboardInterrupt, SystemExit):
				break
			# except Exception as err:
			except:
				# logger.error('Unexpected error when handling following aprs beacon {}'.format(aprs_raw_data[0]))
				logger.exception('Unexpected error when handling following aprs beacon {}'.format(match.group(8)))
	stop_time = time.process_time()
	logger.info('End of parsing, execution time {} seconds'.format(timedelta(seconds=stop_time-start_time)))

	# close the logbook persistent engine
	logbook.pdo_engine.close()

	# For test purpose dump internal logbook structure results
	# Erase result file if exist
	# try:
	# 	os.remove('./htdoc/result.json')
	# 	logger.warning("Previous result file erased.")
	# except FileNotFoundError:
	# 	logger.warning("No previous result file to erase.")

	# # Log the result to output file
	# with open('./htdoc/result.json', 'w') as fp:
	# 	# json.dump(logbook.logbook, fp, indent=4, sort_keys=True, default = lambda obj: obj.__str__() if isinstance(obj, datetime.datetime) )
	# 	json.dump(logbook.logbook, fp, indent=4, sort_keys=True, default = json_converter )

def json_converter(obj):
	if isinstance(obj, datetime.datetime):
		return obj.__str__()

if __name__ == '__main__':
	main()