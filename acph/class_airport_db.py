
import urllib
import logging
import json
from urllib.request import urlopen
from collections import namedtuple

# https://datahub.io/core/airport-codes
AIRPORT_DATAPACKAGE_URL = "https://datahub.io/core/airport-codes/datapackage.json"

AirportCodeValue = namedtuple('AirportCodeValue', ['lat', 'lon', 'icao', 'continent', 'elevation', 'name', 'city', 'country', 'type'])

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
		return AirportCodeValue(float(coordinates[coma_pos+2:]),float(coordinates[:coma_pos]),airport_code['gps_code'],airport_code['continent'],elevation_in_feet,airport_code['name'],airport_code['municipality'],airport_code['iso_country'], airport_code['type'])

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
		instance.logger.info('Loading json airports code from url: {}'.format(airports_code_url))

		if airports_code_url:
			instance.airports = json.loads(urlopen(airports_code_url).read(), object_hook=AirportDatabase.json_airport_decode)

			if not include_closed:
				instance.airports = AirportDatabase.__filter_closed_airport(instance)

		return instance
	
	@staticmethod
	def withJsonFile(json_file_path, include_closed = False):
		instance = AirportDatabase()
		
		with open(json_file_path) as json_file:
			instance.airports = json.load(json_file, object_hook=AirportDatabase.json_airport_decode)
		
		if not include_closed:
			instance.airports = AirportDatabase.__filter_closed_airport(instance)

		instance.logger.warning('Airports code database path is {} ({} airports loaded)'.format(json_file_path, len(instance.airports)))
	
		return instance

