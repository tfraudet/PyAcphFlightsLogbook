import logging
import collections
import itertools

from ogn.parser import parse, ParseError
from geopy import distance
from collections import deque

from acph.class_vptree import AcphVPTree

# OGN constants for sender_type and address_type
OGN_SENDER_TYPES = {
	0 : 'ground_station',
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

ALTITUDE_THRESHOLD = 30				# 30 meters
GROUND_SPEED_THRESHOLD	= 50		# 50km/h
AIRPORT_DISTANCE_THRESHOLD = 4		# 2.5 km
FEETS_TO_METER = 0.3048				# ratio feet to meter

BUFFER_AIRCRAFT_BEACON = 1000		# to keep the last  n aircraft beacons received
NBR_OF_DAY_LOGBOOK = 1				# number of logbook's days to keep in memory
BUFFER_AIRCRAFT_POSITION = 3		# to keep for each aircraft the last n received positions

def feet_to_meter(altitude_in_feet):
	return round(altitude_in_feet * FEETS_TO_METER)

class LRU(collections.OrderedDict):
	'Limit size, evicting the least recently looked-up key when full'

	# def __init__(self, maxsize=128, /, *args, **kwds):
	def __init__(self, maxsize=128, *args, **kwds):
		self.maxsize = maxsize
		super().__init__(*args, **kwds)

	def __getitem__(self, key):
		value = super().__getitem__(key)
		self.move_to_end(key)
		return value

	def __setitem__(self, key, value):
		if key in self:
			self.move_to_end(key)
		super().__setitem__(key, value)
		if len(self) > self.maxsize:
			oldest = next(iter(self))
			del self[oldest]

class FlightsLogBook:
	def __init__(self, receivers_filter, ogndb, airports_db, pdo_engine):
		self.receivers_filter = receivers_filter
		self.ogn_devices_db = ogndb
		self.pdo_engine = pdo_engine
		self.airports = { airports_db[i].icao : airports_db[i] for i in range(0, len(airports_db) ) }
		self.airports_tree =  AcphVPTree([ [item.lat, item.lon, item.icao] for item in airports_db], self.vptree_distance_great_circle)	
		self.logbook = LRU(maxsize=NBR_OF_DAY_LOGBOOK)
		self.buffer_aircraft_beacons = deque(maxlen=BUFFER_AIRCRAFT_BEACON)
		self.logger = logging.getLogger(__name__)
		self.logger.warning(' ACPH Flights Logbook initialized.')
		self.counter_aircraft_beacon_poition = 0

	def vptree_distance_great_circle(self,p1, p2):
		return distance.great_circle((p1[0], p1[1]), (p2[0], p2[1])).km

	def vptree_distance_geodesic(self, p1, p2):
		return distance.geodesic((p1[0], p1[1]), (p2[0], p2[1]), ellipsoid='WGS-84').km
	
	def handlePosition(self, beacon, date):
		self.logger.debug('handle beacon position, raw data: {raw_message}'.format(**beacon))
		if self.isAircraftBeacon(beacon) and self.filteringReceivers(beacon['receiver_name']):
			self.handleAircraftPosition(beacon, date)
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
		if self.receivers_filter is None or len(self.receivers_filter)==0:
			return True
		else:
			return receiver_name in self.receivers_filter

	def findLogbookEntryByID(self, aircraft_id, date, aircraft_type, ognDevice):
		logbook_for_a_date = self.logbook.get(date)

		# Not yet create an entry for this day in the logbook, create it
		if (logbook_for_a_date is None):
			logbook_for_a_date = {}		# create an empty dict
			self.logbook.update({date: logbook_for_a_date})

		# get the list of flights for this aircraft, if the list is not yet created, create it
		logbook_for_aircraft = logbook_for_a_date.get(aircraft_id, None)
		if (logbook_for_aircraft is None):
			logbook_for_aircraft = []	# create an empty list
			logbook_for_a_date.update({aircraft_id: logbook_for_aircraft}) 

		# look for the last flight for this aircraft which is not already landed,
		last_flight_log = None
		last_flight_log_index = len(logbook_for_aircraft) -1
		if last_flight_log_index>=0 and not logbook_for_aircraft[last_flight_log_index]['status'] == 'landed':
			last_flight_log = logbook_for_aircraft[last_flight_log_index]
	
		# if found nothing, first time we received a beacon for this aircraft_id or aircraft_id has already landed, create an new entry in the logbook
		if last_flight_log is None:
			last_flight_log = { 'aircraft_id': aircraft_id,
				 'status': '?',
				 'status_last_airport': '',
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
				 'launch_type' : '#unknown',
				 'flight_id' : len(logbook_for_aircraft) + 1,
				 'last_positions' : deque(maxlen=BUFFER_AIRCRAFT_POSITION)
				}
			logbook_for_aircraft.append(last_flight_log)
		return last_flight_log

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

	def __forDate(self, beacon, date):
		return beacon['timestamp'].strftime('%Y-%m-%d') if date is None else date

	def handleAircraftPosition(self, beacon, date):
		self.counter_aircraft_beacon_poition += 1
		self.logger.info('handle aircraft beacon position #{}, raw data: {raw_message}'.format(self.counter_aircraft_beacon_poition,**beacon))
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
	
		# look for current entry in the logbook for this aircraft_id at the date of the received beacon.
		lg_entry = self.findLogbookEntryByID(aircraft_id,self.__forDate(beacon,date), OGN_SENDER_TYPES[beacon['aircraft_type']], ognDevice)
		if (lg_entry is None):
				raise Exception('No entry found in the logbook for aircarft id {} and the date of {}'.format(aircraft_id,beacon['timestamp'].strftime('%Y-%m-%d')))
		
		# add the receiver who receive the beacon for this aircraft
		if beacon['receiver_name'] not in lg_entry['receivers']:
			lg_entry['receivers'].append(beacon['receiver_name'])

		# add gps coord, speed, altitude, track, clim rate to the buffer for this aircraft
		toSave={
			'altitude': beacon['altitude'],
			'ground_speed': beacon['ground_speed'],
			'climb_rate':  beacon['climb_rate'],
			'track':  beacon['track'],
			'latitude': beacon['latitude'],
			'longitude': beacon['longitude'],
			# 'timestamp': beacon['reference_timestamp']
		}
		lg_entry['last_positions'].appendleft(toSave)

		# handle the new aircraft beacon
		nearest_airport, nearest_airport_distance = self.findNearestAirport_vptree(beacon['latitude'], beacon['longitude'])
		# is_near_coordinates = self.near_coordinates(airport, beacon['latitude'], beacon['longitude'])

		if (nearest_airport is not None):
			is_near_ground = self.near_ground(nearest_airport,beacon['altitude'])
			if (is_near_ground):
				self.handleOnGround(lg_entry, beacon, nearest_airport)
			else:
				if lg_entry['status'] == 'ground' and self.average_ground_speed(lg_entry['last_positions']) >= GROUND_SPEED_THRESHOLD:
					lg_entry.update({'takeoff_time': beacon['timestamp'], 'status' : 'air' , 'status_last_airport': nearest_airport , 'takeoff_airport': nearest_airport })
			
				self.handleAirborne(lg_entry, beacon, ognDevice)
			
			self.pdo_engine.save_aircraft(lg_entry, self.__forDate(beacon, date))
		else:
			#TODO: handle outlanding
			# self.handleOutlanding(lg_entry, beacon, ognDevice)
			pass
		
		# if (self.ogn_devices_db.getAircraftRegistrationById(aircraft_id) == 'F-BSKP'):
		# 	self.logger.warning(
		# 			'Beacon #{}, Sender (type {sender}, callsign: {name}), Receiver callsign: {receiver_name}, {aircraft} {imat} at {altitude}m, speed={ground_speed}km/h,'
		# 			' heading={track}°, climb rate={climb_rate}m/s, nearest airport: {na_icao}/{na_dist}km, (status after handling beacon {status})'
		# 			.format(self.counter_aircraft_beacon_poition,**beacon,
		# 			 imat= self.ogn_devices_db.getAircraftRegistrationById(aircraft_id), aircraft=OGN_SENDER_TYPES[beacon['aircraft_type']],
		# 			 sender=ADDRESS_TYPES[beacon['address_type']], na_icao=nearest_airport, na_dist=nearest_airport_distance, status=lg_entry['status']))
		
		self.updateBufferAicraftBeacons(lg_entry, beacon, ognDevice)

	def findNearestAirport(self, latitude, longitude, distance_threshold = AIRPORT_DISTANCE_THRESHOLD):
		# To calculate distance in pyhton when working with GPS
		#	Geo-py library https://pypi.org/project/geo-py/ and https://github.com/gojuno/geo-py
		#	GeoPy library https://geopy.readthedocs.io/en/latest/#
		nearest_airport_distance = 9999999
		nearest_airpot_icao = None
		for airport in self.airports.values():
			# distance_to_airport = distance.geodesic((latitude, longitude), (airport['lat'],airport['lon']), ellipsoid='WGS-84').km
			distance_to_airport = distance.great_circle((latitude, longitude), (airport['lat'],airport['lon'])).km
			if (distance_to_airport < nearest_airport_distance and distance_to_airport <= distance_threshold):
				nearest_airport_distance = distance_to_airport
				nearest_airpot_icao = airport['icao']

		return nearest_airpot_icao, nearest_airport_distance, 
	
	def findNearestAirport_vptree(self, latitude, longitude, distance_threshold = AIRPORT_DISTANCE_THRESHOLD):
		nearest_airport_distance = float('inf')
		nearest_airpot_icao = None

		resultat = self.airports_tree.get_nearest_neighbor([latitude,longitude,'beacon'])
		self.logger.debug('Nearest airport found is {}, distance is {}km'.format(resultat[1][2], round(resultat[0],3)))

		if (resultat[0] <= distance_threshold):
			nearest_airport_distance = resultat[0]
			nearest_airpot_icao = resultat[1][2]
		
		return nearest_airpot_icao, nearest_airport_distance, 


	def near_coordinates(self, icao, latitude, longitude):
		return True
	
	def near_ground(self, icao, altitude):
		if altitude >= max(0,feet_to_meter(self.airports.get(icao).elevation)-ALTITUDE_THRESHOLD) and altitude <= feet_to_meter(self.airports.get(icao).elevation)+ALTITUDE_THRESHOLD:
			return True
		else:
			return False

	def updateBufferAicraftBeacons(self, lg_entry, beacon, ognDevice):
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
			'longitude': beacon['longitude'],
			# 'timestamp': beacon['reference_timestamp']
		}
		self.buffer_aircraft_beacons.appendleft(toSave)

	def handleOnGround(self, lg_entry, beacon, airport):
		# if lg_entry['status'] == 'ground' and beacon['ground_speed'] >= GROUND_SPEED_THRESHOLD:
		if lg_entry['status'] == 'ground' and self.average_ground_speed(lg_entry['last_positions']) >= GROUND_SPEED_THRESHOLD:
			lg_entry.update({'takeoff_time': beacon['timestamp'], 'status' : 'air' , 'status_last_airport': airport , 'takeoff_airport': airport })
		elif lg_entry['status'] == 'air' and beacon['ground_speed'] < GROUND_SPEED_THRESHOLD:
			# if takeoff have not been detected, cannot compute flight duration
			if not lg_entry.get('takeoff_time') and not lg_entry.get('takeoff_airport'):
				lg_entry.update({'landing_time': beacon['timestamp'], 'status' : 'landed' , 'status_last_airport': airport, 'landing_airport': airport })
			else:
				flight_duration = beacon['timestamp'] - lg_entry.get('takeoff_time')
				lg_entry.update({'landing_time': beacon['timestamp'], 'status' : 'landed' , 'status_last_airport': airport, 'landing_airport': airport, 'flight_duration': str(flight_duration) })
		elif lg_entry['status'] == '?':
			if beacon['ground_speed'] >= GROUND_SPEED_THRESHOLD:
				lg_entry.update({'status' : 'air' , 'status_last_airport': airport })
			else:
				lg_entry.update({'status' : 'ground','status_last_airport': airport })


	def handleAirborne(self, lg_entry, beacon, ognDevice):
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
		self.logger.debug('Try to detect launch type for {aircraft} {imat} at {altitude}m, speed={ground_speed}km/h, heading={track}°, climb rate={climb_rate}m/s'.format(**beacon, imat= self.ogn_devices_db.getAircraftRegistrationById(beacon['address']), aircraft=OGN_SENDER_TYPES[beacon['aircraft_type']], sender=ADDRESS_TYPES[beacon['address_type']]))

		tow_plane = '#unknown'
		# debug_position = 0
		# iterate over the last beacon positions received
		# and look for the aircraft of type tow_plane with minimum distance from this glider 
		for elem in self.buffer_aircraft_beacons:
			if elem['aircraft_type'] == 'tow_plane':
				dist = distance.great_circle((beacon['latitude'], beacon['longitude']), (elem['latitude'],elem['longitude'])).km
				# dist = distance.geodesic((beacon['latitude'], beacon['longitude']), (elem['latitude'],elem['longitude']), ellipsoid='WGS-84').km
				self.logger.debug('distance with {aircraft_type} {imat} (altitude={altitude}, speed={ground_speed}km/h, heading={track}°, climb rate={climb_rate}m/s) is {distplane}km, '.format(**elem,distplane = round(dist,2), imat= self.ogn_devices_db.getAircraftRegistrationById(elem['aircraft_id'])))

				if self.inRangeDistance(dist) and self.inRangeHeading(beacon['track'], elem['track']) and self.inRangeSpeed(beacon['ground_speed'], elem['ground_speed']) and self.inRangeAltitude(beacon['altitude'], elem['altitude']):
					tow_plane = elem['registration']
					self.logger.debug(
						'Found the tow plane {} in the buffer (position {}/ max size {})'
						' --> parameteres: altitude={}, speed={}km/h, heading={}°, climb rate={}m/s, dist to the glider {distplane}km'
						.format(tow_plane, self.buffer_aircraft_beacons.index(elem), BUFFER_AIRCRAFT_BEACON,
						elem['altitude'],elem['ground_speed'],elem['track'],elem['climb_rate'],distplane = round(dist,2)))
					# debug_position = self.buffer_aircraft_beacons.index(elem)
					break

		# Debug purpose
		# if (tow_plane != '#unknown'):
		# 	for elem in itertools.islice(self.buffer_aircraft_beacons, 0, debug_position):
		# 		if (elem['registration'] == tow_plane):
		# 			# self.logger.debug(' == > buffer element is {}'.format(elem))
		# 			self.logger.debug(
		# 					'Found a beacon for {} at position {} that not match'
		# 					' == > parameteres: altitude={}, speed={}km/h, heading={}°, climb rate={}m/s, dist to the glider {distplane}km'
		# 					.format(tow_plane, self.buffer_aircraft_beacons.index(elem),
		# 					elem['altitude'],elem['ground_speed'],elem['track'],elem['climb_rate'],distplane=round(distance.great_circle((beacon['latitude'], beacon['longitude']), (elem['latitude'],elem['longitude'])).km,2)))

		#TODO: detect winch tow launch
		if tow_plane == '#unknown':
			tow_plane = 'winch tow or autonome'

		return tow_plane

	def inRangeDistance(self, dist, distance_precision = 0.4):
		return True if dist <=  distance_precision else False

	def inRangeHeading(self, glider_heading, beacon_heading, degree_precision = 5):
		angle_diff = (glider_heading - beacon_heading) % 360
		if angle_diff > 180:
			angle_diff -= 360
		return True if abs(angle_diff) <= degree_precision else False

	def inRangeSpeed(self, glider_speed, beacon_speed, speed_precision = 20):
		return True if abs(glider_speed-beacon_speed) <=  speed_precision else False

	def inRangeAltitude(self, glider_altitude, beacon_altitude, altitude_precision= 30):
		return True if abs(glider_altitude-beacon_altitude) <=  altitude_precision else False
	
	def average_ground_speed(self, last_positions, n=3):
		last_ground_speeds = [ elem['ground_speed'] for elem in last_positions]
		if len(last_ground_speeds)<=0:
			return 0
		else:
			return sum(itertools.islice(last_ground_speeds, min(n, len(last_ground_speeds))))/min(n,len(last_ground_speeds))


