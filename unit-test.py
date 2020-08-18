import sys
import os
import re
import json
import time
import datetime
from datetime import timedelta
import logging
import logging.config
import logging.handlers

from acph.class_aprs import AcphAprsClient
from acph.class_flights_logbook import FlightsLogBook
from acph.class_ogn_db import OgnDevicesDatabase
from acph.class_flights_logbook_pdo import FlightLogPDO
from acph.class_airport_db import AirportDatabase

def main():
	filepath = sys.argv[1]
	date_of_data = filepath[len(filepath)-14:len(filepath)-4]

	config_files='./unit-test.ini'

	# create logger fo the main
	logging.config.fileConfig(config_files)
	logger = logging.getLogger('acph.main')


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
		# airports_db = AirportDatabase.withPackageUrl()
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

	# test if file that content aprs messages exist
	if not os.path.isfile(filepath):
		logger.error("File path {} does not exist. Exiting...".format(filepath))
		sys.exit()

	# Create the PDO Engine to store the results on the fly: could be JSON or MySql
	# pdo_engine = FlightLogPDO.factory('JSON')
	pdo_engine = FlightLogPDO.factory('MYSQL')

	# create the ACPH Flight logbook and build the logbook for LFHA
	# logbook = FlightsLogBook(receivers_filter={'LFHA'}, ogndb = ogndb, airports_db = listOfAirportsFiltered, pdo_engine = pdo_engine)

	# create the ACPH Flight logbook and handling all the beacons received
	logbook = FlightsLogBook(receivers_filter={}, ogndb = ogndb, airports_db = listOfAirportsFiltered, pdo_engine = pdo_engine)

	# logbook.airports = {k: v for k, v in airports.items() if k[:2] == 'LF'}		# filter only some french airports for test purpose
	# logbook.airports = {k: v for k, v in airports.items() if k in {'LFHA', 'LFHR', 'LFHT', 'LFHP'}}		# filter only some french airports for test purpose
	# logbook.airports = {k: v for k, v in airports.items() if k in {'LFHA'}}		# filter only some french airports for test purpose

	# build the reg-ex to extract raw data from the log
	aprs_reg = re.compile(r'raw data:\s(.*)')

	# open the Logbook persistent engine
	logbook.pdo_engine.open(config_files)

	# and run FlightsLogBook with that data, results are in xxxx
	logger.info('Start to parse the file {}, date of the data is {}'.format(filepath,date_of_data))
	max_line_to_process = -1		# -1 for all
	start_time = time.process_time()
	with open(filepath) as fp:
		numberOfLine = 0
		for line in fp:
			# if max lin reached, stop processing
			if  max_line_to_process>0 and numberOfLine >= max_line_to_process:
				break

			# processing next line
			numberOfLine += 1
			aprs_raw_data = aprs_reg.findall(line)
			if len(aprs_raw_data) == 1:
				# logger.info("line {}, processing raw data: {}".format(numberOfLine, aprs_raw_data[0]))
				logbook.handleBeacon(aprs_raw_data[0], date_of_data)
			# else:
			# 	logger.error("Unable to extract raw aprs message from line : {}".format(line))
	stop_time = time.process_time()
	logger.info('End of parsing, execution time {} seconds'.format(timedelta(seconds=stop_time-start_time)))

	# close the logbook persistent engine
	logbook.pdo_engine.close()

	# For test purpose dump internal logbook structure results
	# Erase result file if exist
	try:
		os.remove('./htdoc/result.json')
		logger.warning("Previous result file erased.")
	except FileNotFoundError:
		logger.warning("No previous result file to erase.")

	# Log the result to output file
	with open('./htdoc/result.json', 'w') as fp:
		# json.dump(logbook.logbook, fp, indent=4, sort_keys=True, default = lambda obj: obj.__str__() if isinstance(obj, datetime.datetime) )
		json.dump(logbook.logbook, fp, indent=4, sort_keys=True, default = json_converter )

def json_converter(obj):
	if isinstance(obj, datetime.datetime):
		return obj.__str__()

if __name__ == '__main__':
	main()