import logging
import logging.config
import os
import configparser

import mysql.connector
import psycopg

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_cors import cross_origin

import datetime

from acph.class_flights_logbook_pdo import FlightLogPDO

app = Flask(__name__)
CORS(app, resources=r'/api/*')  

# Read config file
config_file = './api-server.ini'
config = configparser.ConfigParser()
config.read(config_file)

# Create logger
logging.config.fileConfig(config_file)
logger = logging.getLogger('acph.api')

# set some value from environement variables
if 'DB_NAME' in os.environ:
	config['database']['database'] = os.environ['DB_NAME']
if 'DB_USER' in os.environ:
	config['database']['user'] = os.environ['DB_USER']
if 'DB_PASSWORD' in os.environ:
	config['database']['password'] = os.environ['DB_PASSWORD']
if 'DB_HOST' in os.environ:
	config['database']['host'] = os.environ['DB_HOST']
if 'DB_PORT' in os.environ:
	config['database']['port'] = os.environ['DB_PORT']

if 'SLACK_WEBHOOK_URL' in os.environ:
	config['handler_slackHandler']['args'] = os.environ['SLACK_WEBHOOK_URL']

logger.info('Database connection parameters are: user={}, password={}, database={}, host={}, port={}'.format(
		config['database']['user'],
		config['database']['password'],
		config['database']['database'], 
		config['database']['host'], 
		config['database']['port']))

def get_pdo_engine():
	if 'pdo_engine' not in g:
		_pdo_engine = FlightLogPDO.factory(config['logbook']['persistence'] if 'logbook' in config else 'JSON')
		_pdo_engine.open(config['database'])
		g.pdo_engine = _pdo_engine
	return g.pdo_engine

@app.teardown_appcontext
def close_db(e=None):
	_pdo_engine = g.pop('pdo_engine', None)
	if _pdo_engine is not None:
		_pdo_engine.close()

# Route for getting logbook data for a specific date and airport
@app.route('/api/v1/logbook/<date>/<airport>', methods=['GET'])
def get_logbook_v1(date, airport):
	logger.info(f"API request for logbook data v1: date={date}, airport={airport}")
	
	_pdo_engine=get_pdo_engine()
	try:
		# Validate date format (YYYY-MM-DD)
		parsed_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
		
		if _pdo_engine is None:
			return jsonify({'error': 'Database connection not available'}), 503
		
		# Query the database for the flights on the given date at the given airport
		flights = _pdo_engine.get_flights_by_date_and_airport(parsed_date, airport.upper())
		
		return jsonify({
			'date': date,
			'airport': airport.upper(),
			'data': flights,
			'count': len(flights)
		}), 200
		
	except ValueError:
		return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
	except Exception as e:
		logger.error(f"Error processing API request: {str(e)}")
		return jsonify({'error': str(e)}), 500

# Route for getting logbook data for a specific date and airport
@app.route('/api/v2/logbook/<date>/<airport>', methods=['GET'])
@cross_origin(origins=['https://acph.local','https://aeroclub-issoire.fr'])
def get_logbook_v2(date, airport):
	logger.info(f"API request for logbook data v2: date={date}, airport={airport}")
	
	_pdo_engine=get_pdo_engine()
	try:
		# Validate date format (YYYY-MM-DD)
		parsed_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
		
		if _pdo_engine is None:
			return jsonify({'error': 'Database connection not available'}), 503
		
		# Query the database for the flights on the given date at the given airport
		flights = _pdo_engine.get_flights_by_date_and_airport(parsed_date, airport.upper())
		
		return jsonify({
			# 'date': date,
			# 'airport': airport.upper(),
			'data': flights,
			# 'count': len(flights)
		}), 200
		
	except ValueError:
		return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
	except Exception as e:
		logger.error(f"Error processing API request: {str(e)}")
		return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
@app.route('/', methods=['GET'])
def health_check():
	_pdo_engine=get_pdo_engine()
	if _pdo_engine is None:
		return jsonify({'status': 'error'}), 503
	else:
		return jsonify({'status': 'ok'}), 200

# run using:
#   flask --debug --app api_server run
# or
#   python api_server.py

if __name__ == '__main__':
	app.run(debug=False, host='0.0.0.0', port=5000)