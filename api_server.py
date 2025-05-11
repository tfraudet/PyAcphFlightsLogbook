import logging
import logging.config
import os
import configparser
import signal

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_cors import cross_origin

import datetime

from acph.class_flights_logbook_pdo import FlightLogPDO

app = Flask(__name__)
CORS(app, resources=r'/api/*')  

# Prepare defaults dictionary including environment variables
env_defaults = {key.upper(): value for key, value in os.environ.items()}

# Read config file and create the logger
config_file = './api-server.ini'
config = configparser.ConfigParser(defaults=env_defaults,interpolation=configparser.ExtendedInterpolation())
config.read(config_file)
logging.config.fileConfig(config)
logger = logging.getLogger('acph.api')

# Start ACPH Flights logbook - API server
logger.critical('ACPH Flights logbook - API server version v2025.1')
logger.warning('ACPH Flights logbook - API server starting with config file = {}.'.format(config_file))

logger.info('Database connection parameters are: user={}, password={}, database={}, host={}, port={}'.format(
		config['database']['user'],
		config['database']['password'],
		config['database']['database'], 
		config['database']['host'], 
		config['database']['port']))

logger.info('SLACK_WEBHOOK_URL is: {}'.format(config['handler_slackHandler']['args']))

logger.debug('Debug mode is enabled')

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

@app.after_request
def log_request(response):
	# app.logger.info(f"HTTP {request.method} {request.url} - Params: {request.args} - Status: {response.status_code}")
	logger.info(f'"{request.method} {request.path}" - Status: {response.status_code}')
	return response

def graceful_shutdown(signum, frame):
	logger.warning(f"Received signal {signum}, shutting down gracefully...")
	os._exit(0)

signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)

# run using:
#   flask --debug --app api_server run
# or
#   python api_server.py
# or
#   gunicorn --bind='127.0.0.1:5000' --bind='[::1]:5000' -w 1 --threads 4 'api_server:app'

if __name__ == '__main__':
	app.run(debug=False, host='0.0.0.0', port=5000)