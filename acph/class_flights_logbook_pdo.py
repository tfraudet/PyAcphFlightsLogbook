from __future__ import annotations
from abc import ABC, abstractmethod

import logging
import json
import datetime
import mysql.connector

from mysql.connector import errorcode
from acph.setup_db import TABLES_NAME

from datetime import date
from datetime import timedelta

class FlightLogPDO(ABC):
	def __init__(self):
		self.logger = logging.getLogger(__name__)
		self.logger.debug("Persistence Engine is of type {}".format(self.__class__.__name__))

	@staticmethod
	def factory(target) -> FlightLogPDO:
		if target.upper() == 'JSON':
			return JsonFileFlightLogPDO()
		elif target.upper() == 'MYSQL':
			return MysqlFlightLogPDO()
		else:
			raise ValueError('{} is an invalid value for the FlightLogPDO factory method.'.format(target))

	def save_aircraft(self, logbook: dict, date :str) -> None:
		if logbook is None:
			raise ValueError('Cannot save a null logbook.')

	def open(self, config) -> None:
		self.logger.warning('Open persistence engine of type {}.'.format(self.__class__.__name__))
		pass

	def close(self) -> None:
		self.logger.warning('Close persistence engine.')
		pass

	def purge(self, data_older_than :int = 30) -> None:
		self.logger.warning('Purge data older then {} day(s).'.format(data_older_than))
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

	def purge(self, data_older_than :int = 30) -> None:
		super().purge(data_older_than)


		# delete from `acph_aircraft_logbook` where date < '2020-08-14'
		try:
			cursor = self.get_cursor()

			# compute the purge date 
			purge_date = date.today() - timedelta(days=data_older_than)

			# and execute the query
			query = "delete from `{tablename}` where date < '{purge_date}'".format(tablename=TABLES_NAME['logbook-by-aircraft'], purge_date=purge_date)
			cursor.execute(query)
			self.cnx.commit()
			self.logger.warning('Purge data created before {}, {} records deleted (purge setting={} retention day(s)).'.format(purge_date, cursor.rowcount,data_older_than))
		except mysql.connector.Error as err:
			self.logger.error('Unable to purge logbook entries.')
			self.logger.error(err)
		finally:
			cursor.close()


	def save_aircraft(self, logbook: dict, date :str) -> None:
		super().save_aircraft(logbook, date)
		try:
			cursor = self.get_cursor()

			query = ("INSERT INTO `{tablename}` "
				 "(`date`, `aircraft_id`, `flight_id`, `status`, `status_last_airport`, `aircraft_type`, `aircraft_model`, `registration`, `cn`, `tracked`, `identified`, `takeoff_time`, `takeoff_airport`, `landing_time`, `landing_airport`, `flight_duration`, `launch_type`, `receivers`)"
				 " VALUES (%(date)s, %(aircraft_id)s, %(flight_id)s, %(status)s, %(status_last_airport)s, %(aircraft_type)s, %(aircraft_model)s, %(registration)s, %(cn)s, %(tracked)s, %(identified)s, %(takeoff_time)s, %(takeoff_airport)s, %(landing_time)s, %(landing_airport)s, %(flight_duration)s, %(launch_type)s, %(receivers)s)"
				 " ON DUPLICATE KEY UPDATE "
				 "`status` = %(status)s, "
				 "`status_last_airport` = %(status_last_airport)s, "
				 "`aircraft_type` = %(aircraft_type)s, "
				 "`aircraft_model` = %(aircraft_model)s, "
				 "`registration` = %(registration)s, "
				 "`cn` = %(cn)s, "
				 "`tracked` = %(tracked)s, "
				 "`identified` = %(identified)s, "
				 "`takeoff_time` = %(takeoff_time)s, "
				 "`takeoff_airport` = %(takeoff_airport)s, "
				 "`landing_time` = %(landing_time)s, "
				 "`landing_airport` = %(landing_airport)s, "
				 "`flight_duration` = %(flight_duration)s, "
				 "`launch_type` = %(launch_type)s, "
				 "`receivers` = %(receivers)s"
				 ).format(tablename=TABLES_NAME['logbook-by-aircraft'])

			query_data = {
				'date': date,
				'aircraft_id': logbook['aircraft_id'],
				'flight_id': logbook['flight_id'],
				'status': logbook['status'],
				'status_last_airport': logbook['status_last_airport'],
				'aircraft_type': logbook['aircraft_type'],
				'aircraft_model': logbook['aircraft_model'],
				'registration': logbook['registration'],
				'cn': '' if logbook['cn'] =='#unknown' else logbook['cn'],
				'tracked': logbook['tracked'],
				'identified': logbook['identified'],
				'takeoff_time': logbook['takeoff_time'] if logbook['takeoff_time'] else None,
				'takeoff_airport': logbook['takeoff_airport'],
				'landing_time': logbook['landing_time'] if logbook['landing_time'] else None,
				'landing_airport': logbook['landing_airport'],
				'flight_duration': logbook['flight_duration'],
				'launch_type': logbook['launch_type'],
				'receivers': ','.join(logbook['receivers']),
			}
			cursor.execute(query, query_data)
			self.cnx.commit()
		except mysql.connector.Error as err:
			self.logger.error('Unable to persist logbook entry {} for the date {}'.format(logbook, date))
			self.logger.error(err)
		finally:
			cursor.close()


	def isTablesExists(self):
		try:
			cursor = self.cnx.cursor()
			# query = "SELECT count(*) FROM information_schema.TABLES WHERE (TABLE_SCHEMA = 'wpDB') AND (TABLE_NAME = 'acph_logbook')"
			query = "SHOW TABLES LIKE '{}'".format(TABLES_NAME['logbook-by-aircraft'])
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

	def open(self, config, checkTablesExisting = True) -> None:
		super().open(config)
		try:
			# self.cnx = mysql.connector.connect(option_files=config_file, option_groups='mysql_connector_python')
			self.cnx = mysql.connector.connect(user=config['user'], password=config['password'], database=config['database'], host=config['host'])
			if checkTablesExisting and not self.isTablesExists():
				self.logger.critical('Required tables doesn\'t exists.')
				raise(SystemExit(1))
		except mysql.connector.Error as err:
			self.logger.critical('Exception while opening the MySql connection: {}'.format(err))
			raise(SystemExit(1))

	def close(self) -> None:
		super().close()
		if self.cnx is not None:
			try:
				self.cnx.close()
			except mysql.connector.Error as err:
				self.logger.critical('Exception while closing the MySql connection: {}'.format(err))
			finally:
				self.cnx = None

class JsonFileFlightLogPDO(FlightLogPDO):

	def save_aircraft(self, logbook: dict, date :str ) -> None:
		super().save_aircraft(logbook, date)

		# Log the result to output file
		with open('./db/acph-logbook-{}-{}.json'.format(date, logbook['aircraft_id']), 'w') as fp:
			fp.seek(0)
			# json.dump(logbook.aircrafts_logbook, fp, indent=4, sort_keys=True, default = lambda obj: obj.__str__() if isinstance(obj, datetime.datetime) )
			json.dump({'data': logbook}, fp, indent=4, sort_keys=True, default = self.json_converter )



