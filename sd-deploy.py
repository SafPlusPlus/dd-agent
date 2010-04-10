'''
	Server Density
	www.serverdensity.com
	----
	A web based server resource monitoring application

	Licensed under Simplified BSD License (see LICENSE)
	(C) Boxed Ice 2010 all rights reserved
	
	Documentation: http://www.serverdensity.com/docs/agent/autodeploy/
'''
	
#
# Argument checks
#
import sys

if len(sys.argv) < 5:
	print('Usage: python sd-deploy.py [API URL] [SD URL] [username] [password] [[init]]')
	sys.exit(2)	

#
# Get server details
#

import socket	

# IP
try:
	serverIp = socket.gethostbyname(socket.gethostname())
	
except socket.error as e:
	print(('Unable to get server IP: ' + str(e)))
	sys.exit(2)
	
# Hostname
try:
	serverHostname = hostname = socket.getfqdn()
	
except socket.error as e:
	print(('Unable to get server hostname: ' + str(e)))
	sys.exit(2)

#
# Get latest agent version
#

print('1/4: Downloading latest agent version');
		
import http.client
import urllib.request, urllib.error, urllib.parse

# Request details
try: 
	requestAgent = urllib.request.urlopen('http://www.serverdensity.com/agentupdate/')
	responseAgent = requestAgent.read()
	
except urllib.error.HTTPError as e:
	print(('Unable to get latest version info - HTTPError = ' + str(e)))
	sys.exit(2)
	
except urllib.error.URLError as e:
	print(('Unable to get latest version info - URLError = ' + str(e)))
	sys.exit(2)
	
except http.client.HTTPException as e:
	print('Unable to get latest version info - HTTPException')
	sys.exit(2)
	
except Exception as e:
	import traceback
	print(('Unable to get latest version info - Exception = ' + traceback.format_exc()))
	sys.exit(2)

#
# Define downloader function
#

import md5 # I know this is depreciated, but we still support Python 2.4 and hashlib is only in 2.5. Case 26918
import urllib.request, urllib.parse, urllib.error

def downloadFile(agentFile, recursed = False):
	print(('Downloading ' + agentFile['name']))
	
	downloadedFile = urllib.request.urlretrieve('http://www.serverdensity.com/downloads/sd-agent/' + agentFile['name'])
	
	# Do md5 check to make sure the file downloaded properly
	checksum = md5.new()
	f = file(downloadedFile[0], 'rb')
	
	# Although the files are small, we can't guarantee the available memory nor that there
	# won't be large files in the future, so read the file in small parts (1kb at time)
	while True:
		part = f.read(1024)
		
		if not part: 
			break # end of file
	
		checksum.update(part)
		
	f.close()
	
	# Do we have a match?
	if checksum.hexdigest() == agentFile['md5']:
		return downloadedFile[0]
		
	else:
		# Try once more
		if recursed == False:
			downloadFile(agentFile, True)
		
		else:
			print((agentFile['name'] + ' did not match its checksum - it is corrupted. This may be caused by network issues so please try again in a moment.'))
			sys.exit(2)

#
# Install the agent files
#

# We need to return the data using JSON. As of Python 2.6+, there is a core JSON
# module. We have a 2.4/2.5 compatible lib included with the agent but if we're
# on 2.6 or above, we should use the core module which will be faster
import platform

pythonVersion = platform.python_version_tuple()

# Decode the JSON
if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
	import json
	
	try:
		updateInfo = json.loads(responseAgent)
	except Exception as e:
		print('Unable to get latest version info. Try again later.')
		sys.exit(2)
	
else:
	import minjson
	
	try:
		updateInfo = minjson.safeRead(responseAgent)
	except Exception as e:
		print('Unable to get latest version info. Try again later.')
		sys.exit(2)

# Loop through the new files and call the download function
for agentFile in updateInfo['files']:
	agentFile['tempFile'] = downloadFile(agentFile)			

# If we got to here then everything worked out fine. However, all the files are still in temporary locations so we need to move them
import os
import shutil # Prevents [Errno 18] Invalid cross-device link (case 26878) - http://mail.python.org/pipermail/python-list/2005-February/308026.html

# Make sure doesn't exist already
if os.path.exists('sd-agent/'):
		shutil.rmtree('sd-agent/')

os.mkdir('sd-agent')

for agentFile in updateInfo['files']:
	print(('Installing ' + agentFile['name']))
	
	if agentFile['name'] != 'config.cfg':
		shutil.move(agentFile['tempFile'], 'sd-agent/' + agentFile['name'])
	
print('Agent files downloaded')

#
# Call API to add new server
#

print('2/4: Adding new server')

# Build API payload
import time
timestamp = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())

postData = urllib.parse.urlencode({'name' : serverHostname, 'ip' : serverIp, 'notes' : 'Added by sd-deploy: ' + timestamp })

# Send request
try: 	
	# Password manager
	mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
	mgr.add_password(None, sys.argv[1] + '/1.0/', sys.argv[3], sys.argv[4])
	opener = urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(mgr), urllib.request.HTTPDigestAuthHandler(mgr))
	
	urllib.request.install_opener(opener)
	
	# Build the request handler
	requestAdd = urllib.request.Request(sys.argv[1] + '/1.0/?account=' + sys.argv[2] + '&c=servers/add', postData, { 'User-Agent' : 'Server Density Deploy' })
	
	# Do the request, log any errors
	responseAdd = urllib.request.urlopen(requestAdd)
	
	readAdd = responseAdd.read()
		
except urllib.error.HTTPError as e:
	print(('HTTPError = ' + str(e)))
	
	if os.path.exists('sd-agent/'):
		shutil.rmtree('sd-agent/')
	
except urllib.error.URLError as e:
	print(('URLError = ' + str(e)))
	
	if os.path.exists('sd-agent/'):
		shutil.rmtree('sd-agent/')
	
except http.client.HTTPException as e: # Added for case #26701
	print(('HTTPException' + str(e)))
	
	if os.path.exists('sd-agent/'):
		shutil.rmtree('sd-agent/')
		
except Exception as e:
	import traceback
	print(('Exception = ' + traceback.format_exc()))
	
	if os.path.exists('sd-agent/'):
		shutil.rmtree('sd-agent/')

# Decode the JSON
if int(pythonVersion[1]) >= 6: # Don't bother checking major version since we only support v2 anyway
	import json
	
	try:
		serverInfo = json.loads(readAdd)
	except Exception as e:
		print('Unable to add server.')
		
		if os.path.exists('sd-agent/'):
			shutil.rmtree('sd-agent/')
		
		sys.exit(2)
	
else:
	import minjson
	
	try:
		serverInfo = minjson.safeRead(readAdd)
	except Exception as e:
		print('Unable to add server.')
		
		if os.path.exists('sd-agent/'):
			shutil.rmtree('sd-agent/')
		
		sys.exit(2)
		
print(('Server added - ID: ' + str(serverInfo['data']['serverId'])))

#
# Write config file
#

print('3/4: Writing config file')

configCfg = '[Main]\nsd_url: http://' + sys.argv[2] + '\nagent_key: ' + serverInfo['data']['agentKey'] + '\napache_status_url: http://www.example.com/server-status/?auto'

try:
	f = open('sd-agent/config.cfg', 'w')
	f.write(configCfg)
	f.close()

except Exception as e:
	import traceback
	print(('Exception = ' + traceback.format_exc()))
	
	if os.path.exists('sd-agent/'):
		shutil.rmtree('sd-agent/')

print('Config file written')

#
# Install init.d
#

if len(sys.argv) == 6:
	
	print('4/4: Installing init.d script')
	
	shutil.copy('sd-agent.init', '/etc/init.d/sd-agent')
	
	import subprocess
	
	print('Setting permissions')
	
	df = subprocess.Popen(['chmod', '0755', '/etc/init.d/sd-agent'], stdout=subprocess.PIPE).communicate()[0]
	
	print('chkconfig')
	
	df = subprocess.Popen(['chkconfig', '--add', 'sd-agent'], stdout=subprocess.PIPE).communicate()[0]
	
	print('Setting paths')
	
	path = os.path.realpath(__file__)
	path = os.path.dirname(path)
	
	df = subprocess.Popen(['ln', '-s', path + '/sd-agent/', '/usr/bin/sd-agent'], stdout=subprocess.PIPE).communicate()[0]
	
	print('Install completed')
	
	print('Launch: /etc/init.d/sd-agent start')
	
else:
	
	print('4/4: Not installing init.d script')
	print('Install completed')
	
	path = os.path.realpath(__file__)
	path = os.path.dirname(path)
	
	print('Launch: python ' + path + '/sd-agent/agent.py start')
