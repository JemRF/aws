/*rf2awsiot.js Interface between RF Module serial interface and Amazon AWS IOT Core
---------------------------------------------------------------------------------                                                                               
 J. Evans May 2018
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
 WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN 
 CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                                                       
 
 Revision History                                                                  
 V1.00 - Release
 
 -----------------------------------------------------------------------------------
*/
 
'use strict';
var awsIot = require('aws-iot-device-sdk');

//Set Fahrenheit=0 display in centigrade
const Fahrenheit=0;

//Set the AWS Thing Prefix
const thingPrefix = "Device_";
const thingName = "RaspberryPi";

//Set the AWS End Point e.g. a1jj45tr9rhhbq.iot.us-west-2.amazonaws.com
const endPoint = 'a1j34fr34frhhbq.iot.us-west-2.amazonaws.com';

// Replace the values below with a unique client identifier and custom host endpoint provided 
// in AWS IoT cloud NOTE: client identifiers must be unique within your AWS account; if a client 
// attempts to connect with a client identifier which is already in use, the existing connection 
// will be terminated.

var thingShadows = awsIot.thingShadow({
   keyPath: '/home/pi/aws-keys/private.pem.key',
  certPath: '/home/pi/aws-keys/certificate.pem.crt',
    caPath: '/home/pi/aws-keys/root-CA.crt',
  clientId: thingName,
      host: endPoint
});

//Library used for serial port access
var SerialPort = require('serialport');
var port = new SerialPort('/dev/ttyAMA0');

var inStr="";

var data = {
	deviceID: "",
    command: "",
    value: ""
};

//
// Client token value returned from thingShadows.update() operation
//
var clientTokenUpdate;

thingShadows.on('connect', function() {
	console.log('AWS Connected');	
});

thingShadows.on('error', function(err) {
  console.log('Error: ', err.message);
});

thingShadows.on('status', 
    function(thingName, stat, clientToken, stateObject) {
       console.log('received '+stat+' on '+thingName+': '+
                   JSON.stringify(stateObject));
//
// These events report the status of update(), get(), and delete() 
// calls.  The clientToken value associated with the event will have
// the same value which was returned in an earlier call to get(),
// update(), or delete().  Use status events to keep track of the
// status of shadow operations.
//
    });

thingShadows.on('delta', 
    function(thingName, stateObject) {
       console.log('received delta on '+thingName+': '+
                   JSON.stringify(stateObject));
    });

thingShadows.on('timeout',
    function(thingName, clientToken) {
       console.log('received timeout on '+thingName+
                   ' with token: '+ clientToken);
//
// In the event that a shadow operation times out, you'll receive
// one of these events.  The clientToken value associated with the
// event will have the same value which was returned in an earlier
// call to get(), update(), or delete().
//
    });
	
// Read data that is available but keep the stream from entering "flowing mode"
port.on('readable', function () {
  var n;
  var deviceID;
  var payload;
  var llapMsg;
  
  inStr+=port.read().toString('utf8');
  n = inStr.search("a"); //start charachter for llap message
  if (n>0) inStr = inStr.substring(n, inStr.length); //chop off data preceding start charachter
  if (inStr.length>=12){ //we have an llap message!
    while (inStr!=""){
		data.command="";
		llapMsg=inStr.substring(1,12);
		console.log(llapMsg);
		data.deviceID=llapMsg.substring(0,2);
		deviceID=thingPrefix+data.deviceID;
		if (llapMsg.substring(2,6)=="TMPA") {
			data.value=llapMsg.substring(6,13);
			data.command="TMPA";
		}
		if (llapMsg.substring(2,6)=="TMPB") {
			data.value=llapMsg.substring(6,13);
			data.command="TMPB";
		}
		if (llapMsg.substring(2,5)=="HUM") {
			data.value=llapMsg.substring(5,13);
			data.command="HUM";
		}
		if (llapMsg.substring(2,6)=="TMPC") {
			data.value=llapMsg.substring(6,13);
			data.command="TMPC";
		}
		if (llapMsg.substring(2,8)=="BUTTON") {
			data.value=llapMsg.substring(8,13);
			data.command="BUTTON";
		}
		if (llapMsg.substring(2,10)=="SLEEPING") {
			data.value="ASLEEP";
			data.command="STATE";
		}
	    if (llapMsg.substring(2,7)=="AWAKE") {
			data.value="AWAKE";
			data.command="STATE";
		}
		if (llapMsg.substring(2,6)=="BATT") {
			data.value=llapMsg.substring(6,13);
			data.command="BATT";
		}
		if (llapMsg.substring(2,9)=="STARTED"){
			data.value="";
			data.command="STARTED";
		} 
		if (data.command!="" && data.command!="STATE"){ 
			data.value.replace('-',' ');
			data.value.trim();
			if (Fahrenheit){
				if (data.command=="TMP"){
					data.value=data.value*1.8+32;
					data.value=data.value.toFixed(2);
				}
			}
				
			var awsData =  "{\"state\":{\"reported\":{\""+deviceID+"\": {\""+data.command+"\":\""+data.value+"\"}}}}";
			var awsJSON = JSON.parse(awsData);
			console.log(awsJSON);
			
			//
			// After connecting to the AWS IoT platform, register interest in the
			// Thing Shadow named 'RaspberryPi', for example.
			//
			
			// Once registration is complete, update the Thing Shadow named
			// 'RaspberryPi', for example, with the latest device state and save the clientToken
			// so that we can correlate it with status or timeout events.
			//
			// Thing shadow state
			//
			
			if (data.command=="TMP"){ //Set to only send temperature reading to AWS. Remove this and all will get sent
				console.log("Registering Thing:"+thingName);
			    thingShadows.register(thingName);
				clientTokenUpdate = thingShadows.update(thingName, awsJSON);
				//
				// The update method returns a clientToken; if non-null, this value will
				// be sent in a 'status' event when the operation completes, allowing you
				// to know whether or not the update was successful.  If the update method
				// returns null, it's because another operation is currently in progress and
				// you'll need to wait until it completes (or times out) before updating the 
				// shadow.
				//
				if (clientTokenUpdate === null)
					{
					console.log('update shadow failed, operation still in progress');
					}
				}				
			}
		if (inStr.length>12) 
			inStr=inStr.substring(12,inStr.length);
		else
			inStr="";
	  }  
  }
});


port.on('error', function(err) {
  console.log('Error: ', err.message);
});
