
import mysql.connector
from mysql.connector import errorcode

TABLES_NAME = {}
TABLES_NAME['logbook'] = 'acph_logbook'
TABLES_NAME['logbook-by-icao'] = 'acph_icao_logbook'

TABLES = {}
TABLES['logbook'] = (
	"CREATE TABLE `acph_logbook` ("
	"  `id` BIGINT NOT NULL AUTO_INCREMENT,"
	"  `date` DATE NOT NULL,"
	"  `status` enum('?','ground', 'air', 'landed') NOT NULL,"
	"  `aircraft_id` VARCHAR(6) NOT NULL,"
	"  `aircraft_type` VARCHAR(255),"
	"  `aircraft_model` VARCHAR(255),"
	"  `registration` LONGTEXT,"
	"  `cn` VARCHAR(2),"
	"  `tracked` enum('Y', 'N'),"
	"  `identified` enum('Y', 'N'),"
	"  `takeoff_time` DATETIME,"
	"  `takeoff_airport` VARCHAR(4),"
	"  `landing_time` DATETIME,"
	"  `landing_airport` VARCHAR(4),"
	"  `flight_duration` TIME DEFAULT 0,"
	"  `launch_type` VARCHAR(255),"
	"  PRIMARY KEY (`id`)"
	") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci")

TABLES['logbook-by-icao'] = (
	"CREATE TABLE `acph_icao_logbook` ("
	"  `date` DATE NOT NULL,"
	"  `icao` VARCHAR(4) NOT NULL,"
	"  `logbook` MEDIUMTEXT,"
	"  PRIMARY KEY (`date`, `icao`)"
	") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci")

def createTables(cursor):
	for table_name in TABLES:
		table_description = TABLES[table_name]
		# print('Table desciption is: {}'.format(table_description))
		try:
			print("  Creating table {}: ".format(table_name), end='')
			cursor.execute(table_description)
		except mysql.connector.Error as err:
			if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
				print("already exists.")
			else:
				print(err.msg)
		else:
			print("OK")

def main():

	print("ACPH LogBook - initialize database tables.")
	try:
		cnx = mysql.connector.connect(option_files='./acph-logbook.ini', option_groups='mysql_connector_python')

		cursor = cnx.cursor()
		createTables(cursor)
		cursor.close()
	except mysql.connector.Error as err:
		if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
			print("Something is wrong with your user name or password")
		elif err.errno == errorcode.ER_BAD_DB_ERROR:
			print("Database does not exist")
		else:
			print(err)
	else:
		cnx.close()

if __name__ == '__main__':
	main()