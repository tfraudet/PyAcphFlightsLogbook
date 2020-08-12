import logging
import collections


from ogn.parser import parse, ParseError
from geopy import distance
from collections import deque

# OGN constants for sender_type and address_type
OGN_SENDER_TYPES = {
	1 : 'glider',
	2 : 'tow_plane',
	3 : 'helicopter_rotorcraft',
	4 : 'parachute',
	5 : 'drop_plane',
	6 : 'hang_glider',
	7 : 'para_glider',
	8 : 'powered_aircraft',
	9 : 'jet_aircraft',
	10 : 'ufo',
	11 : 'balloon',
	12 : 'airship',
	13 : 'uav',
	15 : 'static_object',
}

ADDRESS_TYPES = {
	0 : 'random',
	1 : 'icao',
	2 : 'flarm',
	3 : 'ogn',
}

ALTITUDE_THRESHOLD = 30				# 30 meter
GROUND_SPEED_THRESHOLD	= 40		# 40km/h
AIRPORT_DISTANCE_THRESHOLD = 1.0		# 1 km
FEETS_TO_METER = 0.3048				# ratio feets to meter

BUFFER_POSITION_SIZE = 500			# to buffer the last n  position received

def feet_to_meter(altitude_in_feet):
	return round(altitude_in_feet * FEETS_TO_METER)

class FlightsLogBook:
	def __init__(self, airports_icao, ogndb, pdo_engine):
		self.airports_icao = airports_icao
		self.ogn_devices_db = ogndb
		self.pdo_engine = pdo_engine
		self.airports = None
		self.aircrafts_logbook = {}
		self.buffer_position = deque(maxlen=BUFFER_POSITION_SIZE)
		self.logger = logging.getLogger(__name__)
	
	def handlePosition(self, beacon, date):
		self.logger.debug('handle beacon position, raw data: {raw_message}'.format(**beacon))
		if self.isAircraftBeacon(beacon) and self.filteringReceivers(beacon['receiver_name']):
			# try:
				self.handleAircraftPosition(beacon, date)
			# except Exception as ex:
			# 	self.logger.warning(ex)
		else:
			self.logger.debug('handle beacon position, not an aircraft or receiver name filetered [beacon type is {beacon_type}, receiver name is {receiver_name}]'.format(**beacon))

	def handleStatus(self, beacon, date):
		self.logger.debug('handle beacon status, raw data: {raw_message}'.format(**beacon))

	def handleComment(self, beacon, date):
		self.logger.info('handle beacon comment, raw data: {raw_message}'.format(**beacon))

	def handleServer(self, beacon, date):
		self.logger.info('handle beacon server, raw data: {raw_message}'.format(**beacon))

	def handleBeacon(self, raw_message, date = None):
		try:
			beacon = parse(raw_message)
			self.logger.debug('Receive beacon {aprs_type}, raw data: {raw_message}'.format(**beacon))
			handlers = {
				'position': self.handlePosition,
				'status': self.handleStatus,
				'comment': self.handleComment,
				'server': self.handleServer,
			}
			func = handlers.get(beacon.get('aprs_type'),lambda beacon: self.logger.error('aprs type ' + beacon['aprs_type'] + ' is unknown, beacon not handle.'))
			func(beacon, date)
		except ParseError:
			logging.error("Exception occurred", exc_info=True)
	
	def isAircraftBeacon(self, beacon):
		return beacon['beacon_type'] == 'aprs_aircraft'

	def isReceiverBeacon(self, beacon):
		return beacon['beacon_type'] == 'aprs_receiver'

	def filteringReceivers(self, receiver_name):
		return receiver_name in self.airports_icao

	def findLogbookEntryByID(self, aircraft_id, date, aircraft_type, ognDevice):
		logbook_for_a_date = self.aircrafts_logbook.get(date)

		# Not yet create an entry for this day in the logbook, create it
		if (logbook_for_a_date is None):
			logbook_for_a_date = []		# create an empty list
			self.aircrafts_logbook.update({date: logbook_for_a_date})

		# look for an entry for aircraft_id in the logbook
		entry_for_aircraft = None
		for anAircraftEntry in logbook_for_a_date:
			if (anAircraftEntry['aircraft_id']) == aircraft_id and not anAircraftEntry['status'] == 'landed':
				entry_for_aircraft = anAircraftEntry
				break
	
		# if found nothing, first time we received a beacon for this aircraft_id or aircraft_id has already landed, create an new entry in the logbook
		if entry_for_aircraft is None:
			entry_for_aircraft = { 'aircraft_id': aircraft_id,
				 'status': '?',
				 'receivers': [],
				 'aircraft_type' : aircraft_type,
				 'aircraft_model': ognDevice.get('aircraft_model'),
				 'registration': ognDevice.get('registration'),
				 'cn': ognDevice.get('cn'),
				 'tracked': ognDevice.get('tracked'),
				 'identified': ognDevice.get('identified'),
				 'takeoff_time': '',
				 'takeoff_airport': '',
				 'landing_time' : '',
				 'landing_airport' : '',
				 'flight_duration': '',
				 'launch_type' : '#unknown'
				}
			logbook_for_a_date.append(entry_for_aircraft)
		return entry_for_aircraft

	def findOgnAircraftById(self, aircraft_id):
			ognDevice = self.ogn_devices_db.getAircraftById(aircraft_id)
			# if we don't found this aircraft_id in OGN DB return a fake entry
			if ognDevice is None:
				ognDevice = {
					"device_type":"#unknown",			# normaly F or I or O
					"device_id": aircraft_id,
					"aircraft_model":"#unknown",
					"registration":"#unknown",
					"cn":"#unknown",
					"tracked":"N",
					"identified":"N"}
			return ognDevice



	def handleAircraftPosition(self, beacon, date):
		self.logger.info('handle aircraft beacon position, raw data: {raw_message}'.format(**beacon))
		aircraft_id = beacon['address']

		# aircraft need to be in OGN database to be handle
		# ognDevice = self.ogn_devices_db.getAircraftById(aircraft_id)
		# if ognDevice is None:
		# 	raise Exception("Device id {} is unknow in OGN database".format(aircraft_id))

		# handle even aircraft_if not in OGN DB (findOgnAircraftById return a fake OgnDb entry if aircarft_if not exists in the DB)
		ognDevice = self.findOgnAircraftById(aircraft_id)

		# round some value from aprs message
		beacon['altitude'] = round(beacon['altitude'])
		beacon['ground_speed'] = round(beacon['ground_speed'])
		beacon['climb_rate'] = round(beacon['climb_rate'],1)
		# self.logger.debug('Sender (type {sender}, callsign: {name}), Receiver callsign: {receiver_name}, {aircraft} {address} at {altitude}m, speed={ground_speed}km/h, heading={track}°, climb rate={climb_rate}m/s'.format(**beacon, aircraft=OGN_SENDER_TYPES[beacon['aircraft_type']], sender=ADDRESS_TYPES[beacon['address_type']]))
	
		self.logger.debug('Sender (type {sender}, callsign: {name}), Receiver callsign: {receiver_name}, {aircraft} {imat} at {altitude}m, speed={ground_speed}km/h, heading={track}°, climb rate={climb_rate}m/s'.format(**beacon, imat= self.ogn_devices_db.getAircraftRegistrationById(aircraft_id), aircraft=OGN_SENDER_TYPES[beacon['aircraft_type']], sender=ADDRESS_TYPES[beacon['address_type']]))
		
		# look for current entry in the logbook for this aircraft_id at the date of the received beacon.

		lg_entry = self.findLogbookEntryByID(aircraft_id,beacon['timestamp'].strftime('%Y-%m-%d') if date is None else date, OGN_SENDER_TYPES[beacon['aircraft_type']], ognDevice)
		if (lg_entry is None):
				raise Exception('No entry found in the logbook for aircarft id {} and the date of {}'.format(aircraft_id,beacon['timestamp'].strftime('%Y-%m-%d')))
		
		# add the receiver who receive the beacon for this aircraft
		if beacon['receiver_name'] not in lg_entry['receivers']:
			lg_entry['receivers'].append(beacon['receiver_name'])

		# handle the new aircraft beacon
		nearest_airport, nearest_airport_distance = self.findNearestAirport(beacon['latitude'], beacon['longitude'])
		# is_near_coordinates = self.near_coordinates(airport, beacon['latitude'], beacon['longitude'])

		if (nearest_airport is not None):
			is_near_ground = self.near_ground(nearest_airport,beacon['altitude'])
			if (is_near_ground):
				self.handleOnGround(lg_entry, beacon, nearest_airport)
			else:
				self.handleAirborne(lg_entry, beacon, ognDevice)
			
			self.pdo_engine.save(self.aircrafts_logbook)
		else:
			#TODO: handle outlanding
			# self.handleOutlanding(lg_entry, beacon, ognDevice)
			pass
		
		self.updatePosition(lg_entry, beacon, ognDevice)

	def findNearestAirport(self, latitude, longitude, distance_threshold = AIRPORT_DISTANCE_THRESHOLD):
		# To calculate distance in pyhton when working with GPS
		#	Geo-py library https://pypi.org/project/geo-py/ and https://github.com/gojuno/geo-py
		#	GeoPy library https://geopy.readthedocs.io/en/latest/#
		#
		#	PyGeodesy library https://github.com/mrJean1/PyGeodesy and doc https://mrjean1.github.io/PyGeodesy/
		#	PyProj4	library http://pyproj4.github.io/pyproj/stable/
		#	
		#	some refererences:
		#		https://janakiev.com/blog/gps-points-distance-python/
		#		https://medium.com/@petehouston/calculate-distance-of-two-locations-on-earth-using-python-1501b1944d97
		#
		# use Geo-Py to calculate the distance between  the beacon and the known airports , return the one with the minimal distance
		nearest_airport_distance = 9999999
		nearest_airpot_icao = None
		for airport in self.airports.values():
			# distance_to_airport = distance.geodesic((latitude, longitude), (airport['lat'],airport['lon']), ellipsoid='WGS-84').km
			distance_to_airport = distance.great_circle((latitude, longitude), (airport['lat'],airport['lon'])).km
			if (distance_to_airport < nearest_airport_distance and distance_to_airport <= distance_threshold):
				nearest_airport_distance = distance_to_airport
				nearest_airpot_icao = airport['icao']

		return nearest_airpot_icao, nearest_airport_distance, 
	
	def near_coordinates(self, icao, latitude, longitude):
		return True
	
	def near_ground(self, icao, altitude):
		if altitude >= max(0,feet_to_meter(self.airports.get(icao).get('elevation'))-ALTITUDE_THRESHOLD) and altitude <= feet_to_meter(self.airports.get(icao).get('elevation'))+ALTITUDE_THRESHOLD:
			return True
		else:
			return False

	def updatePosition(self, lg_entry, beacon, ognDevice):
		aircraft_id = beacon['address']

		toSave={
			'aircraft_id': aircraft_id,
			'aircraft_type': OGN_SENDER_TYPES[beacon['aircraft_type']],
			'registration': ognDevice['registration'],
			'altitude': beacon['altitude'],
			'ground_speed': beacon['ground_speed'],
			'climb_rate':  beacon['climb_rate'],
			'track':  beacon['track'],
			'latitude': beacon['latitude'],
			'longitude': beacon['longitude']
		}
		self.buffer_position.appendleft(toSave)
		pass


	def handleOnGround(self, lg_entry, beacon, airport):
		if lg_entry['status'] == 'ground' and beacon['ground_speed'] >= GROUND_SPEED_THRESHOLD:
			lg_entry.update({'takeoff_time': beacon['timestamp'], 'status' : 'air' , 'takeoff_airport': airport })
		elif lg_entry['status'] == 'air' and beacon['ground_speed'] < GROUND_SPEED_THRESHOLD:
			# if takeoff have not been detected, cannot compute flight duration
			if not lg_entry.get('takeoff_time') and not lg_entry.get('takeoff_airport'):
				lg_entry.update({'landing_time': beacon['timestamp'], 'status' : 'landed' , 'landing_airport': airport })
			else:
				flight_duration = beacon['timestamp'] - lg_entry.get('takeoff_time')
				lg_entry.update({'landing_time': beacon['timestamp'], 'status' : 'landed' , 'landing_airport': airport, 'flight_duration': str(flight_duration) })
		elif lg_entry['status'] == '?':
			if beacon['ground_speed'] >= GROUND_SPEED_THRESHOLD:
				lg_entry.update({'status' : 'air' })
			else:
				lg_entry.update({'status' : 'ground' })


	def handleAirborne(self, lg_entry, beacon, ognDevice):
		# if lg_entry['status'] == '?':
		# 	if beacon['ground_speed'] >= GROUND_SPEED_THRESHOLD:
		# 		lg_entry.update({'status' : 'air' })
		# 	else:
		# 		lg_entry.update({'status' : 'ground' })
		# else:
		if lg_entry['launch_type'] == '#unknown' and lg_entry['status'] == 'air':
			switcher = {
				'glider' : self.detectLaunchType,
				'tow_plane' : 'autonome',
				'helicopter_rotorcraft' : 'autonome',
				'powered_aircraft' :'autonome',
			}
			result = switcher.get(OGN_SENDER_TYPES[beacon['aircraft_type']],'#unknown')
			if isinstance(result, collections.Callable):
				result = result(lg_entry, beacon, ognDevice)
			lg_entry['launch_type'] = result

	# for glider detect launch type
	# right now detect only tow_plane, dectecting winch launch is not supported
	def detectLaunchType(self, lg_entry, beacon, ognDevice, distance_threshold = 0.5):
		self.logger.debug('Detect launch type for {aircraft} {imat} at {altitude}m, speed={ground_speed}km/h, heading={track}°, climb rate={climb_rate}m/s'.format(**beacon, imat= self.ogn_devices_db.getAircraftRegistrationById(beacon['address']), aircraft=OGN_SENDER_TYPES[beacon['aircraft_type']], sender=ADDRESS_TYPES[beacon['address_type']]))

		tow_plane = '#unknown'
		# iterate over the last beacon positions received
		# and look for the aircraft of type tow_plane with minimum distance from this glider 
		for elem in self.buffer_position:
			if elem['aircraft_type'] == 'tow_plane':
				dist = distance.geodesic((beacon['latitude'], beacon['longitude']), (elem['latitude'],elem['longitude']), ellipsoid='WGS-84').km
				self.logger.debug('distance with {aircraft_type} {imat} (altitude={altitude}, speed={ground_speed}km/h, heading={track}°, climb rate={climb_rate}m/s) is {distplane}km, '.format(**elem,distplane = round(dist,2), imat= self.ogn_devices_db.getAircraftRegistrationById(elem['aircraft_id'])))

				if self.inRangeDistance(dist) and self.inRangeHeading(beacon['track'], elem['track']) and self.inRangeSpeed(beacon['ground_speed'], elem['ground_speed']) and self.inRangeAltitude(beacon['altitude'], elem['altitude']):
					tow_plane = elem['registration']
					break
		
		#TODO: detect winch tow launch
		if tow_plane == '#unknown':
			tow_plane = 'winch tow or autonome'

		return tow_plane

	def inRangeDistance(self, dist, distance_precision = 0.2):
		return True if dist <=  distance_precision else False

	def inRangeHeading(self, glider_heading, beacon_heading, degree_precision = 5):
		angle_diff = (glider_heading - beacon_heading) % 360
		if angle_diff > 180:
			angle_diff -= 360
		return True if abs(angle_diff) <= degree_precision else False

	def inRangeSpeed(self, glider_speed, beacon_speed, speed_precision = 5):
		return True if abs(glider_speed-beacon_speed) <=  speed_precision else False

	def inRangeAltitude(self, glider_altitude, beacon_altitude, altitude_precision= 10):
		return True if abs(glider_altitude-beacon_altitude) <=  altitude_precision else False


