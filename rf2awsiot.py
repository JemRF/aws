#!/usr/bin/env python
"""
rf2awsiot.py v1 Serial to AWS interface 
---------------------------------------------------------------------------------
                                                                                  
 J. Evans June 2018
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
 WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN 
 CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                                       
                                                                                  
 Revision History                                                                  
 V1.00 - Release
"""

import serial
import globals
import time
import sys
import thread
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import logging
import json
import argparse
from time import sleep
global RFList
global LocationList
global numrf
DEBUG = True
Fahrenheit = False

# Custom Shadow callback
def customShadowCallback_Update(payload, responseStatus, token):
    # payload is a JSON string ready to be parsed using json.loads(...)
    # in both Py2.x and Py3.x
    if responseStatus == "timeout":
        print("Update request " + token + " time out!")
    if responseStatus == "accepted":
        print("~~~~~~~~~~~~~~~~~~~~~~~")
        print("Update request with token: " + token + " accepted!")
        print("property: " + str(payload))
        print("~~~~~~~~~~~~~~~~~~~~~~~\n\n")
    if responseStatus == "rejected":
        print("Update request " + token + " rejected!")

def customShadowCallback_Delete(payload, responseStatus, token):
    if responseStatus == "timeout":
        print("Delete request " + token + " time out!")
    if responseStatus == "accepted":
        print("~~~~~~~~~~~~~~~~~~~~~~~")
        print("Delete request with token: " + token + " accepted!")
        print("~~~~~~~~~~~~~~~~~~~~~~~\n\n")
    if responseStatus == "rejected":
        print("Delete request " + token + " rejected!")

def dprint(message):
	if (DEBUG):
		print message

def ProcessMessageThread(value, value2, DevId, type):
	try:
			thread.start_new_thread(ProcessMessage, (value, value2, DevId, type, ) )
	except:
			print "Error: unable to start thread"

def aws_send(device_id, value, property):
	JSONPayload = '{"state":{"reported":{"'+str(device_id)+'": {"'+str(property)+'": "'+ str(value) + '"}}}}'
	dprint(JSONPayload)
	deviceShadowHandler.shadowUpdate(JSONPayload, customShadowCallback_Update, 5)
			
def ProcessMessage(value, value2, DevId, type, property):
# Notify the host that there is new data from a sensor (e.g. door open)
	try:
		dprint("Processing data : DevId="+str(DevId)+",Type="+str(type)+",Value1="+str(value)+",Value2="+str(value2))

		DevId="Device_"+DevId;
		#Send switch sensor value to host
		if type==1:
				value=value[1:]
				if value=='OF' or value=='OFF':
						aws_send(DevId, "Open", property)
				if value=='ON':
						aws_send(DevId, "Closed", property)

		#Send battery level to host
		if type==2:
				aws_send(DevId, value, property)

		#Send temperature to host
		if type==3:
				if Fahrenheit:
						value = value*1.8+32
						value = round(value,2)
				
				aws_send(str(DevId), str(value), property)

		#Send humidity to host
		if type==4:
				if Fahrenheit:
						value = value*1.8+32
						value = round(value,2)
				
				aws_send(DevId, str(value), "TMP")
				aws_send(DevId, str(value2), "HUM")
				
	except Exception as e: dprint(e)
	return(0)

def main():
        currvalue=''
        tempvalue=-999;
        
        # loop until the serial buffer is empty

        start_time = time.time()
        
        #try:
        while True:

				# declare to variables, holding the com port we wish to talk to and the speed
				port = '/dev/ttyAMA0'
				baud = 9600

				# open a serial connection using the variables above
				ser = serial.Serial(port=port, baudrate=baud)

				# wait for a moment before doing anything else
				sleep(0.2)        
				while ser.inWaiting():
						# read a single character
						char = ser.read()
						# check we have the start of a LLAP message
						if char == 'a':
								sleep(0.01)
								start_time = time.time()
								
								# start building the full llap message by adding the 'a' we have
								llapMsg = 'a'

								# read in the next 11 characters form the serial buffer
								# into the llap message
								llapMsg += ser.read(11)

								# now we split the llap message apart into devID and data
								devID = llapMsg[1:3]
								data = llapMsg[3:]
								
								dprint(time.strftime("%c")+ " " + llapMsg)
																
								if data.startswith('BUTTON'):
										sensordata=data[5:].strip('-')
										if currvalue<>sensordata or currvalue=='':
												currvalue=sensordata
												ProcessMessage(currvalue, 0, devID,1, "BUTTON")

								if data.startswith('BTN'):
										sensordata=data[2:].strip('-')
										if currvalue<>sensordata or currvalue=='':
												currvalue=sensordata
												ProcessMessage(currvalue, 0, devID,1, "BUTTON")

								if data.startswith('TMPA'):
										sensordata=str(data[4:].rstrip("-"))								
										currvalue=sensordata
										ProcessMessage(currvalue, 0, devID,3, "TMPA")
								
								if data.startswith('ANAA'):
										sensordata=str(data[4:].rstrip("-"))								
										currvalue=sensordata
										ProcessMessage(currvalue, 0, devID,3, "ANAA")
								
								if data.startswith('ANAB'):
										sensordata=str(data[4:].rstrip("-"))								
										currvalue=sensordata
										ProcessMessage(currvalue, 0, devID,3, "ANAB")
								
								if data.startswith('TMPC'):
										sensordata=str(data[4:].rstrip("-"))								
										currvalue=sensordata
										ProcessMessage(currvalue, 0, devID,3, "TMPC")
								
								if data.startswith('TMPB'): #Temperature followed by humidity
										sensordata=str(data[4:].rstrip("-"))								
										tempbdata=sensordata
																				
								if data.startswith('HUM'):
										sensordata=str(data[3:].rstrip("-"))								
										currvalue=sensordata
										if tempbdata<>"" and sensordata<>"":
											ProcessMessage(tempbdata, sensordata, devID,4, "")
											tempbdata=''
												
								# check if battery level is being sent axxBATTn.nn-
								if data.startswith('BATT'):
										sensordata=data[4:].strip('-')
										currvalue=sensordata 
										ProcessMessage(currvalue, 0, devID,2, "BATT")
				elapsed_time = time.time() - start_time
				if (elapsed_time > 2):
						currvalue=""
						sensordata=""
						tempbdata=""
				sleep(0.2)
				#except:
				#        print "Error: unable to start thread"
           
if __name__ == "__main__":
        # Read in command-line parameters
		parser = argparse.ArgumentParser()
		parser.add_argument("-e", "--endpoint", action="store", required=True, dest="host", help="Your AWS IoT custom endpoint")
		parser.add_argument("-r", "--rootCA", action="store", required=True, dest="rootCAPath", help="Root CA file path")
		parser.add_argument("-c", "--cert", action="store", dest="certificatePath", help="Certificate file path")
		parser.add_argument("-k", "--key", action="store", dest="privateKeyPath", help="Private key file path")
		parser.add_argument("-w", "--websocket", action="store_true", dest="useWebsocket", default=False,help="Use MQTT over WebSocket")
		parser.add_argument("-n", "--thingName", action="store", dest="thingName", default="Bot", help="Targeted thing name")
		parser.add_argument("-id", "--clientId", action="store", dest="clientId", default="basicShadowUpdater", help="Targeted client id")

		args = parser.parse_args()
		host = args.host
		rootCAPath = args.rootCAPath
		certificatePath = args.certificatePath
		privateKeyPath = args.privateKeyPath
		useWebsocket = args.useWebsocket
		thingName = args.thingName
		clientId = args.clientId

		if args.useWebsocket and args.certificatePath and args.privateKeyPath:
			parser.error("X.509 cert authentication and WebSocket are mutual exclusive. Please pick one.")
			exit(2)

		if not args.useWebsocket and (not args.certificatePath or not args.privateKeyPath):
			parser.error("Missing credentials for authentication.")
			exit(2)

		# Configure logging
		logger = logging.getLogger("AWSIoTPythonSDK.core")
		logger.setLevel(logging.DEBUG)
		streamHandler = logging.StreamHandler()
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		streamHandler.setFormatter(formatter)
		logger.addHandler(streamHandler)

		# Init AWSIoTMQTTShadowClient
		myAWSIoTMQTTShadowClient = None
		if useWebsocket:
			myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(clientId, useWebsocket=True)
			myAWSIoTMQTTShadowClient.configureEndpoint(host, 443)
			myAWSIoTMQTTShadowClient.configureCredentials(rootCAPath)
		else:
			myAWSIoTMQTTShadowClient = AWSIoTMQTTShadowClient(clientId)
			myAWSIoTMQTTShadowClient.configureEndpoint(host, 8883)
			myAWSIoTMQTTShadowClient.configureCredentials(rootCAPath, privateKeyPath, certificatePath)

		# AWSIoTMQTTShadowClient configuration
		myAWSIoTMQTTShadowClient.configureAutoReconnectBackoffTime(1, 32, 20)
		myAWSIoTMQTTShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
		myAWSIoTMQTTShadowClient.configureMQTTOperationTimeout(5)  # 5 sec

		# Connect to AWS IoT
		myAWSIoTMQTTShadowClient.connect()

		# Create a deviceShadow with persistent subscription
		deviceShadowHandler = myAWSIoTMQTTShadowClient.createShadowHandlerWithName(thingName, True)

		# Delete shadow JSON doc
		deviceShadowHandler.shadowDelete(customShadowCallback_Delete, 5)
		main()



   
   


