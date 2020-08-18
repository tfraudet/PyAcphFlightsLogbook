from ogn.client import AprsClient
from ogn.client import settings

import socket
import logging

# PACKAGE_VERSION = '0.9.7'
# APRS_APP_VER = PACKAGE_VERSION[:3]

def create_aprs_login(user_name, pass_code, app_name, app_version, aprs_filter=None):
	if not aprs_filter:
		return "user {} pass {} vers {} {}\n".format(user_name, pass_code, app_name, app_version)
	else:
		return "user {} pass {} vers {} {} filter {}\n".format(user_name, pass_code, app_name, app_version, aprs_filter)

class AcphAprsClient(AprsClient):
	def __init__(self, aprs_user, aprs_passcode, aprs_filter='', settings=settings):
		super().__init__(aprs_user, aprs_filter, settings)
		self.logger = logging.getLogger(__name__)
		self.settings.APRS_APP_NAME = 'acph-ogn-client'
		self.settings.APRS_APP_VER = '1.0-beta'
		self.aprs_passcode = aprs_passcode
		self.logger.warning("Connect to OGN as {} with filter '{}'".format(aprs_user, (aprs_filter if aprs_filter else 'full-feed')))

	def connect(self):
			# create socket, connect to server, login and make a file object associated with the socket
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

			if self.aprs_filter:
				port = self.settings.APRS_SERVER_PORT_CLIENT_DEFINED_FILTERS
			else:
				port = self.settings.APRS_SERVER_PORT_FULL_FEED

			self.sock.connect((self.settings.APRS_SERVER_HOST, port))
			self.logger.debug('Server port {}'.format(port))

			login = create_aprs_login(self.aprs_user, self.aprs_passcode, self.settings.APRS_APP_NAME, self.settings.APRS_APP_VER, self.aprs_filter)
			self.sock.send(login.encode())
			self.sock_file = self.sock.makefile('rw')

			self._kill = False
		
	def disconnect(self):
		super().disconnect()
		self.logger.warning('Disconnected from APRS server.')

