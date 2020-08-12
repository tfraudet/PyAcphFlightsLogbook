class AircraftLogbook(object):
	def __init__(self, device_id):
		self._device_id = device_id
		self._aircraft_type = ''
		self._receivers = ''

	@property
	def device_id(self):
		return self._device_id

	@property
	def aircraft_type(self):
		return self._aircraft_type

	@property
	def receivers(self):
		return self._receivers
	
	@receivers.deleter
	def receivers(self):
		del self._receivers

	@receivers.setter
	def _aircraft_type(self, new_type):
		pass

	@aircraft_type.setter
	def aircraft_type(self, new_type):
		self._aircraft_type = new_type

	def __str__(self):
		return {
			'aircraft_id': self.device_id, 
			'aircraft_type': self.aircraft_type,
			'receivers' : self.receivers,
		}


