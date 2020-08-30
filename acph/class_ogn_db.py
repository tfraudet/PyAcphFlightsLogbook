
import urllib
import logging
import json
from urllib.request import urlopen

OGN_DDB_URL = "http://ddb.glidernet.org/"
OGN_DDB_DEVICES_LIST_URL = "http://ddb.glidernet.org/download/?j=1"

class OgnDevicesDatabase:
	devices = None

	def __init__(self):
		self.logger = logging.getLogger(__name__)
		self.logger.setLevel(logging.INFO)
		self.devices = {}

	@staticmethod
	def withURL():
		instance = OgnDevicesDatabase()
		
		json_url = urlopen(OGN_DDB_DEVICES_LIST_URL)
		data = json.loads(json_url.read())
		for item in data['devices']:
			instance.devices[item['device_id']] = item

		instance.logger.info('OGN devices datbase, {} devices loaded from url {}'.format(len(instance.devices),OGN_DDB_DEVICES_LIST_URL))
		return instance
	
	@staticmethod
	def withJsonFile(json_ogn_ddb_file):
		instance = OgnDevicesDatabase()

		with open(json_ogn_ddb_file) as json_file:
			data = json.load(json_file)
			# instance.devices = data['devices'] 			v0.1
			for item in data['devices']:
				instance.devices[item['device_id']] = item

		instance.logger.info('OGN devices datbase, {} devices loaded from json file {}'.format(len(instance.devices),json_ogn_ddb_file))			
		return instance

	def getAircraftById(self, device_id):
		# for aDevice in iter(self.devices):				v0.1
		# 	if aDevice['device_id'] == device_id:
		# 		return aDevice
		# return None
		return self.devices.get(device_id,None)

	def getAircraftModelById(self, device_id):
		aircraft = self.getAircraftById(device_id)
		if (aircraft is not None):
			return aircraft['aircraft_model']
		else:
			return None

	def getAircraftRegistrationById(self, device_id):
		aircraft = self.getAircraftById(device_id)
		if (aircraft is not None):
			return aircraft['registration']
		else:
			return None

	def getAircraftCnById(self, device_id):
		aircraft = self.getAircraftById(device_id)
		if (aircraft is not None):
			return aircraft['cn']
		else:
			return None

	def getAircraftTypeById(self, device_id):
		aircraft = self.getAircraftById(device_id)
		if (aircraft is not None):
			return aircraft['device_type']
		else:
			return None

	def isAircraftTrackedById(self, device_id):
		aircraft = self.getAircraftById(device_id)
		if (aircraft is not None and aircraft['tracked'] =='Y'):
			return True
		else:
			return False

	def isAircraftIdentifiedById(self, device_id):
		aircraft = self.getAircraftById(device_id)
		if (aircraft is not None and aircraft['identified'] =='Y'):
			return True
		else:
			return False

