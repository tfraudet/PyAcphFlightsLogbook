from __future__ import annotations
from abc import ABC, abstractmethod

import logging
import json
import datetime
import mysql.connector
from mysql.connector import errorcode
from acph.setup_db import TABLES_NAME

class FlightLogPDO(ABC):
	def __init__(self):
		self.logger = logging.getLogger(__name__)
		self.logger.debug("PDO Engine is of type {}".format(self.__class__.__name__))

	@staticmethod
	def factory(target) -> FlightLogPDO:
		if target == 'JSON':
			return JsonFileFlightLogPDO()
		elif target == 'MYSQL':
			return MysqlFlightLogPDO()
		else:
			raise ValueError('{} is an invalid value for the FlightLogPDO factory method.'.format(target))

	def save(self, logbook: dict) -> None:
		if logbook is None:
			raise ValueError('Cannot save a null logbook.')

		for key, value in logbook.items():
			self.saveLogbookForDate(key, value)

	def open(self):
		self.logger.info('Open PDO engine.')
		pass

	def close(self):
		self.logger.info('Close PDO engine.')
		pass

	@abstractmethod
	def saveLogbookForDate(self, date :str, logbook: dict) -> None:
		pass

	def json_converter(self, obj):
		if isinstance(obj, datetime.datetime):
			return obj.__str__()


class MysqlFlightLogPDO(FlightLogPDO):
	def __init__(self):
		super().__init__()
		self.cnx = None

	# Inspiration here: https://bitworks.software/en/2019-03-12-tornado-persistent-mysql-connection-strategy.html
	def get_cursor(self):
		try:
			self.cnx.ping(reconnect=True, attempts=3, delay=5)
		except mysql.connector.Error as err:
			self.logger.warning("Connection with MySql DB probably loose following the session time-out, try to reconnect. Error is {}".format(err))
			self.open(False)
		return self.cnx.cursor()

	def saveLogbookForDate(self, date :str, logbook: dict) -> None:
		super().saveLogbookForDate(date, logbook)
		try:
			cursor = self.get_cursor()
			# query = ("INSERT INTO {tablename} "
			# 		 "(date, status, aircraft_id, aircraft_type, aircraft_model, registration, cn, tracked, identified, takeoff_time, takeoff_airport, landing_time, landing_airport, flight_duration, launch_type)"
			# 		 " VALUES (%(date)s, %(status)s, %(aircraft_id)s, %(aircraft_type)s, %(aircraft_model)s, %(registration)s, %(cn)s, %(tracked)s, %(identified)s, %(takeoff_time)s, %(takeoff_airport)s, %(landing_time)s, %(landing_airport)s, %(flight_duration)s, %(launch_type)s) ")
			# query_data = {
			# 	'date': date,
			# 	'status': lg_entry['status'],
			# 	'aircraft_id': lg_entry['aircraft_id'],
			# 	'aircraft_type': lg_entry['aircraft_type'],
			# 	'aircraft_model': lg_entry['aircraft_model'],
			# 	'registration': lg_entry['registration'],
			# 	'cn': lg_entry['cn'],
			# 	'tracked': lg_entry['tracked'],
			# 	'identified': lg_entry['identified'],
			# 	'takeoff_time': lg_entry['takeoff_time'],
			# 	'takeoff_airport': lg_entry['takeoff_airport'],
			# 	'landing_time': lg_entry['landing_time'],
			# 	'landing_airport': lg_entry['landing_airport'],
			# 	'flight_duration': lg_entry['flight_duration'],
			# 	'launch_type': lg_entry['launch_type'],
			# 	}

			query = ("INSERT INTO `{tablename}` "
				 "(`date`, `icao`, `logbook`)"
				 " VALUES (%(date)s, %(icao)s, %(logbook)s) "
				 "ON DUPLICATE KEY UPDATE `logbook` = %(logbook)s").format(tablename=TABLES_NAME['logbook-by-icao'])
			# query.format(tablename=TABLES_NAME['logbook-by-icao'])

			query_data = {
				'date': date,
				'icao': 'LFHA',
				'logbook' : json.dumps({'data': logbook}, sort_keys=True, default = self.json_converter )
			}
			# json_to_str = json.dumps({'data': logbook}, sort_keys=True, default = self.json_converter )
			# cursor.execute(query, (date, 'lfha', 'test'))
			cursor.execute(query, query_data)
			self.cnx.commit()
		except mysql.connector.Error as err:
			self.logger.error('Unable to persist logbook entry.' )
			self.logger.error(err)
		finally:
			cursor.close()

	def isTablesExists(self):
		try:
			cursor = self.cnx.cursor()
			# query = "SELECT count(*) FROM information_schema.TABLES WHERE (TABLE_SCHEMA = 'wpDB') AND (TABLE_NAME = 'acph_logbook')"
			query = "SHOW TABLES LIKE '{}'".format(TABLES_NAME['logbook'])
			cursor.execute(query)
			row = cursor.fetchone()
			if row is not None:
				return True
			else:
				return False
		except mysql.connector.Error as err:
			self.logger.critical('Unable to verify if required tables are existing.' )
			self.logger.critical(err)
			raise(SystemExit)
		finally:
			cursor.close()

	def open(self, checkTablesExisting = True):
		super().open()
		try:
			self.cnx = mysql.connector.connect(option_files='./acph-logbook.ini', option_groups='mysql_connector_python')
			if checkTablesExisting and not self.isTablesExists():
				self.logger.critical('Required tables doesn\'t exists.')
				raise(SystemExit(1))
		except mysql.connector.Error as err:
			self.logger.critical('Exception while opening the MySql connection: {}'.format(err))
			raise(SystemExit(1))

	def close(self):
		super().close()
		if self.cnx is not None:
			try:
				self.cnx.close()
			except mysql.connector.Error as err:
				self.logger.critical('Exception while closing the MySql connection: {}'.format(err))
			finally:
				self.cnx = None

class JsonFileFlightLogPDO(FlightLogPDO):

	def saveLogbookForDate(self, date :str, logbook: dict) -> None:
		super().saveLogbookForDate(date, logbook)

		# Log the result to output file
		with open('./db/acph-logbook-{}.json'.format(date), 'w') as fp:
			fp.seek(0)
			# json.dump(logbook.aircrafts_logbook, fp, indent=4, sort_keys=True, default = lambda obj: obj.__str__() if isinstance(obj, datetime.datetime) )
			json.dump({'data': logbook}, fp, indent=4, sort_keys=True, default = self.json_converter )



