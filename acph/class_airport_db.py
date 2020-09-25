
from __future__ import annotations
from abc import ABC, abstractmethod

import urllib
import logging
import json
import csv
from urllib.request import urlopen
from collections import namedtuple

# https://datahub.io/core/airport-codes, 
AIRPORT_DATAPACKAGE_URL = "https://datahub.io/core/airport-codes/datapackage.json"

AirportCodeValue = namedtuple('AirportCodeValue', ['lat', 'lon', 'icao', 'continent', 'elevation', 'name', 'city', 'country', 'type', 'runways'])
AirportRunwayValue = namedtuple('Runway', ['direction', 'length_ft', 'width_ft', 'surface'])

class AbstractAirportsDatabase(ABC):
	def __init__(self):
		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(logging.INFO)
		self.airports = dict()

	def filterByContinent(self,continent):	
		return {k: v for k, v in self.airports.items() if v.continent == continent}

	def filterByCountry(self,country):	
		return {key: value for (key, value) in self.airports.items() if value.country == country}

	@abstractmethod
	def getAirportByIcao(self, icao : str) -> AirportCodeValue:
		pass

# data from https://ourairports.com/data/
class OurAirportsDatabase(AbstractAirportsDatabase):
	def getAirportByIcao(self, icao : str) -> AirportCodeValue:
		return None

	@staticmethod
	def withCsvFile(csv_file_path, include_closed = False):
		csv_airports_file =  csv_file_path + '/airports.csv'
		csv_runways_file = csv_file_path + '/runways.csv'
		instance = OurAirportsDatabase()
		
		# handle airport code
		with open(csv_airports_file, mode='r') as csv_file:
			reader = csv.DictReader(csv_file)
			instance.__handleAirportCodes(reader, include_closed)

		instance.logger.info('Airports code database, {} airports loaded from csv file {}'.format(len(instance.airports), csv_airports_file))	

		# handle airport runways 
		with open(csv_runways_file, mode='r') as csv_file:
			reader = csv.DictReader(csv_file)
			instance.__handleAirportRunways(reader)
		instance.logger.info('Airports runways database, {} airports loaded from csv file {}'.format(len(instance.airports), csv_runways_file))	

		return instance

	@staticmethod
	def withUrl(url_path = 'https://ourairports.com/data', include_closed = False):
		# https://ourairports.com/data/airports.csv
		# https://ourairports.com/data/runways.csv
		csv_airports_url =  url_path + '/airports.csv'
		csv_runways_url = url_path + '/runways.csv'
		instance = OurAirportsDatabase()
		
		# handle airport codes
		with urllib.request.urlopen(csv_airports_url) as response:
			lines = [l.decode('utf-8') for l in response.readlines()]
			reader = csv.DictReader(lines)
			instance.__handleAirportCodes(reader, include_closed)
		instance.logger.info('Airports code database, {} airports loaded from URL {}'.format(len(instance.airports), csv_airports_url))	

		# handle airport runways 
		with urllib.request.urlopen(csv_runways_url) as response:
			lines = [l.decode('utf-8') for l in response.readlines()]
			reader = csv.DictReader(lines)
			instance.__handleAirportRunways(reader)
		instance.logger.info('Airports runways database, {} airports loaded from URL {}'.format(len(instance.airports), csv_runways_url))	

		return instance

	def __handleAirportCodes(self, reader, include_closed):
		for row in reader:
			if not include_closed and row['type'] == 'closed':
				pass
			else:
				if not row['elevation_ft']:
					elevation_in_feet = 0
				else:
					elevation_in_feet = int(row['elevation_ft'])

				# if gps_code is empty try to use ident
				icao = row['ident'] if not row['gps_code'] else row['gps_code']

				self.airports[icao] = AirportCodeValue(
					float(row['latitude_deg']),
					float(row['longitude_deg']),
					icao,
					row['continent'],
					elevation_in_feet,
					row['name'],
					row['municipality'],
					row['iso_country'],
					row['type'],
					[])

	def __handleAirportRunways(self, reader):
		for row in reader:
			if row['airport_ident'] in self.airports:
				self.airports.get(row['airport_ident']).runways.append(AirportRunwayValue(
					row['le_ident'] + '/' + row['he_ident'],
					row['length_ft'],
					row['width_ft'],
					row['surface'],
				))

class AirportDatabase:
	def __init__(self):
		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(logging.INFO)

	def filterByContinent(self,continent):	
		# [ <output value>  for <element> in <list>  <optional criteria>  ]
		return [ item for item in self.airports if item.continent == continent]

	def filterByCountry(self,country):	
		# [ <output value>  for <element> in <list>  <optional criteria>  ]
		return [ item for item in self.airports if item.country == country]
	
	@staticmethod
	def json_airport_decode(airport_code):
		coordinates = airport_code['coordinates']
		coma_pos = coordinates.find(',')
		if not airport_code['elevation_ft']:
			elevation_in_feet = 0
		else:
			elevation_in_feet = int(airport_code['elevation_ft'])
		return AirportCodeValue(float(coordinates[coma_pos+2:]),float(coordinates[:coma_pos]),airport_code['gps_code'],airport_code['continent'],elevation_in_feet,airport_code['name'],airport_code['municipality'],airport_code['iso_country'], airport_code['type'],[])

	@staticmethod
	def __filter_closed_airport(airport_db):
		return [ item for item in airport_db.airports if not item.type == 'closed']

	@staticmethod
	def withPackageUrl( data_package_url = AIRPORT_DATAPACKAGE_URL, include_closed = False):
		instance = AirportDatabase()
		json_url = urlopen(data_package_url)
		datapackage = json.loads(json_url.read())
		instance.logger.warning('Loading data package {} v{} from {} ({} airports, modified on {})'.format(datapackage['title'], datapackage['version'], datapackage['homepage'], datapackage['count_of_rows'], datapackage['datahub']['modified']))

		# look for airport code in json format
		airports_code_url = None
		for item in datapackage['resources']:
			if item['name'] == 'airport-codes_json': airports_code_url = item['path']

		# load data in json format
		if airports_code_url:
			instance.airports = json.loads(urlopen(airports_code_url).read(), object_hook=AirportDatabase.json_airport_decode)

			if not include_closed:
				instance.airports = AirportDatabase.__filter_closed_airport(instance)

		instance.logger.info('Airports code database, {} airports loaded from url {}'.format(len(instance.airports), airports_code_url))	
		return instance
	
	@staticmethod
	def withJsonFile(json_file_path, include_closed = False):
		instance = AirportDatabase()
		
		with open(json_file_path) as json_file:
			instance.airports = json.load(json_file, object_hook=AirportDatabase.json_airport_decode)
		
		if not include_closed:
			instance.airports = AirportDatabase.__filter_closed_airport(instance)

		instance.logger.info('Airports code database, {} airports loaded from json file {}'.format(len(instance.airports), json_file_path))	
		return instance

