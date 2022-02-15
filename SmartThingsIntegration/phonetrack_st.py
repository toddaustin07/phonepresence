import subprocess
import socket
import platform

import os
import errno
import sys
import _thread
import time
import re
import configparser

import requests

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

HOME_STATES={
    2: "REACHABLE",
    8: "DELAY",
    # 4: "STALE",
} 


PORTNUMBER = 50001
BRIDGEADDR = '192.168.1.140:8082'

SCANTYPE_IP = 1
SCANTYPE_ARP = 2
SCANTYPE_NONE = -1

CONFIGFILE = 'phonetrack.cfg'
LOGFILE = 'phonetrack.log'
DEVICE_LIST = []
NOTPRESENT_RETRIES = 5
PINGINTERVAL = 12


class logger(object):
	
	def __init__(self, toconsole, tofile, fname, append):
	
		self.toconsole = toconsole
		self.savetofile = tofile

		self.os = platform.system()
		if self.os == 'Windows':
			os.system('color')
		
		if tofile:
			self.filename = fname
			if not append:
				try:
					os.remove(fname)
				except:
					pass
			
	def __savetofile(self, msg):
		
		with open(self.filename, 'a') as f:
			f.write(f'{time.strftime("%c")}  {msg}\n')
	
	def __outputmsg(self, colormsg, plainmsg):
		
		if self.toconsole:
			print (colormsg)
		if self.savetofile:
			self.__savetofile(plainmsg)
	
	def info(self, msg):
		colormsg = f'\033[33m{time.strftime("%c")}  \033[96m{msg}\033[0m'
		self.__outputmsg(colormsg, msg)
		
	def warn(self, msg):
		colormsg = f'\033[33m{time.strftime("%c")}  \033[93m{msg}\033[0m'
		self.__outputmsg(colormsg, msg)
		
	def error(self, msg):
		colormsg = f'\033[33m{time.strftime("%c")}  \033[91m{msg}\033[0m'
		self.__outputmsg(colormsg, msg)
		
	def hilite(self, msg):
		colormsg = f'\033[33m{time.strftime("%c")}  \033[97m{msg}\033[0m'
		self.__outputmsg(colormsg, msg)
		
	def debug(self, msg):
		colormsg = f'\033[33m{time.strftime("%c")}  \033[37m{msg}\033[0m'
		self.__outputmsg(colormsg, msg)
		

class mobiledevice(object):
	
	def __init__(self, ipaddr, name, retries):
		
		self.ipaddress = ipaddr
		self.name = name
		self.offline_retries = retries
		self.present = 'unknown'
		self.notpresentcounter = 0
		self.skipupdates = 0

	def ping(self):

		MESSAGE = b"Marco"
		MESSAGE_PORT = 5353

		try:
			with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
				s.settimeout(1)
				s.sendto(MESSAGE, (self.ipaddress, MESSAGE_PORT))
		except Exception as e:
				log.error (f"Failed to reach {self.name}'s cellphone: {e}")

	def update_presence(self, present):
		
		self.present = present
		
	def ispresent(self):
		return self.present
		
		
class mobilescanner(object):
	
	def __init__(self):

		self.tracktype = SCANTYPE_NONE

	def setup(self):

		self.os = platform.system()
		cmd = ''

		if self.os == 'Windows':
			cmd = 'where'
		else:
			cmd = 'which'

		if subprocess.run(f"{cmd} ip", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
			log.info("Using 'IP' to find tracked devices")
			self.tracktype = SCANTYPE_IP
		elif subprocess.run(f"{cmd} arp", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
			log.info("Using 'ARP' to find tracked devices")
			self.tracktype = SCANTYPE_ARP
		else:
			log.error("IP or ARP commands not available on this computer")
			return False

		return True
		
	def find_with_ip(self):
		# Queries the network neighbors and lists found IP's
		state_filter = " nud " + " nud ".join(HOME_STATES.values()).lower()
		cmd = f"ip neigh show {state_filter}".split()
		neighbors = subprocess.run(cmd, shell=False, capture_output=True, text=True)
		return [_.split()[0] for _ in neighbors.stdout.splitlines()]
		
	def find_with_arp(self):
		# Queries the arp table and lists found IP's
		cmd = "arp -a".split()
		neighbors = subprocess.run(cmd, shell=False, capture_output=True, text=True)
		return [_.split()[0] for _ in neighbors.stdout.splitlines() if _.count(".") == 3]

	def scan(self):
		if self.tracktype == SCANTYPE_IP:
			return self.find_with_ip()
			
		elif self.tracktype == SCANTYPE_ARP:
			return self.find_with_arp()
			
		else:
			print ("ERROR: unknown tracktype", self.tracktype)

class SourcePortAdapter(HTTPAdapter):
	""""Transport adapter" that allows us to set the source port."""
	def __init__(self, port, *args, **kwargs):
		self._source_port = port
		super(SourcePortAdapter, self).__init__(*args, **kwargs)

	def init_poolmanager(self, connections, maxsize, block=False):
		self.poolmanager = PoolManager(
			num_pools=connections, maxsize=maxsize,
			block=block, source_address=('', self._source_port))

class httprequest(object):
	
	def __init__(self, port):
		
		self.s = requests.Session()
		self.s.mount('http://', SourcePortAdapter(port))
	
	
	def send(self, url):

		HTTP_OK = 200
		
		host = re.search('//([\d.:]+)/', url).group(1)
		
		headers = { 'Host' : host,
					'Content-Type' : 'application/json'}
		
		oksent = False
	
		while oksent == False:
		
			try:
				r = self.s.post(url, headers=headers)
				
			except OSError as error:
				if OSError != errno.EADDRINUSE:
					log.error (error)
				else:
					log.error ("Address already in use; retrying")
				
				time.sleep(.250)
			else:
				oksent = True

		if r.status_code != HTTP_OK:
			log.error (f'HTTP ERROR {r.status_code} sending: {url}')
			

#-----------------------------------------------------------------------

def presence_changed(requestor, phone):
	
	if phone.skipupdates > 150:
		log.info (f'{phone.name} Presence refreshed to = {phone.ispresent()}')
	else:
		log.hilite (f'{phone.name} Presence changed to = {phone.ispresent()}')
	
	BASEURL = f'http://{BRIDGEADDR}'

	state = ''
	
	if phone.ispresent():
		state = 'present'
	else:
		state = 'notpresent'
	
	requestor.send(BASEURL + '/' + phone.name + '/presence/' + state)
	

############################### MAIN ###################################


CONFIG_FILE_PATH = os.getcwd() + os.path.sep + CONFIGFILE

parser = configparser.ConfigParser()
if not parser.read(CONFIG_FILE_PATH):
	print (f'\nConfig file is missing ({CONFIG_FILE_PATH})\n')
	exit(-1)
	
if parser.get('config', 'console_output').lower() == 'yes':
	conoutp = True	
else:
	conoutp = False

if parser.get('config', 'logfile_output').lower() == 'yes':
	logoutp = True
	LOGFILE = parser.get('config', 'logfile')
else:
	logoutp = False
	LOGFILE = ''
	
log = logger(conoutp, logoutp, LOGFILE, False)

phonelist = parser.get('config', 'phone_ips')
namelist = parser.get('config', 'phone_names')
retrylist = parser.get('config', 'phone_offline_retries')

PINGINTERVAL = int(parser.get('config', 'ping_interval'))

phones = phonelist.split(',')
names = namelist.split(',')
retries = retrylist.split(',')

i = 0
for phone in phones:
	DEVICE_LIST.append(mobiledevice(phone.strip(), names[i].strip(), int(retries[i].strip())))
	i += 1
	
PORTNUMBER = int(parser.get('config', 'port'))
BRIDGEADDR = parser.get('config', 'bridge_address')

requestor = httprequest(PORTNUMBER)

scanner = mobilescanner()
if scanner.setup():

	try:

		while True:
			
			log.info ('Pinging')
			for device in DEVICE_LIST:
				device.ping()

			time.sleep(.5)
			iplist = scanner.scan()

			for device in DEVICE_LIST:
				priorstate = device.ispresent()
				
				if device.ipaddress in iplist:
					device.update_presence(True)
					device.notpresentcounter = 0
					if priorstate != True or device.skipupdates > 150:
						presence_changed(requestor, device)
						device.skipupdates = 0
					else:
						device.skipupdates += 1
				
				else:
					device.notpresentcounter += 1
					log.debug (f'\t{device.name}: Not present count = {device.notpresentcounter}')
					
					if device.notpresentcounter >= device.offline_retries:
						device.update_presence(False)
						device.notpresentcounter = 0
						if priorstate != False or device.skipupdates > 150:
							presence_changed(requestor, device)
							device.skipupdates = 0
						else:
							device.skipupdates += 1
					
			log.info ('Scan complete')
			time.sleep(PINGINTERVAL-.5)
			
	except KeyboardInterrupt:
		log.warn ('\nAction interrupted by user...ending thread')
		
else:
	log.error ('Failed to initialize scanner')
	exit(-1)
