# phonetrack application

This Python script uses a technique, borrowed from here => https://github.com/mudape/iphonedetect, to track presence of mobile phones on the home network.  On a periodic basis (every 12 seconds, for example) it sends a UDP message to port 5353 (mDNS) of the mobile phone's IP address to try and force the phone to renew its existence on local network address tables.  The script then examines the local ARP table (via IP commands) to see if the phone's IP address is included.  If it is, it is presumed present. If it is not, a number of subsequent retries are attempted (e.g. 5-10) before declaring the phone not present.  

## Known Issues
With the latest iOS (version 15), this technique is not 100% reliable.  A number of retries (configurable) may be required to ensure false away-states are not reported, which can result in true not-present reports to take up to 2 minutes or more.  More critically, upon arrival of an iPhone that is asleep, in some cases detection may not occur until the iPhone is woken up by the user.

## Two versions available
If you want to try the phone monitoring without connecting to SmartThings, you can use the standalone version of the application in the root directory.
If you want a setup where you have SmartThings presence devices that get phone tracking updates, then use the application in the SmartThingsIntegration folder.

## Standalone version

- Download phonetrack.py and phonetrack.cfg onto a computer (Linux, Windows, Mac) with **Python 3.7 or later**.
- Edit the phonetrack.cfg file to specify your phone IP address(es) (should be static); also include short friendly names for each phone (no spaces or special characters)
- Invoke the program:  
```
python3 phonetrack.py
```

### Log file (phonetrack.log)
In addition to the messages displayed on stdout, entries are also saved to a log file called phonetrack.log in the current working directory.  **Note that this log file will be erased and reset each time the program is executed.**  So copy it to another file if you want to save it before running the program again.

#### What to look for
The key info to be monitored in the console output or log file is the 'Not present count' message.  The fewer times this is seen, the better.  Sequential counts of 5 or more while the iPhone is actually at home indicate that the iPhone is not being detected on the network.  

### Configuration File (phonetrack.cfg)
The phonetrack.cfg file where the phone IP address and friendly names are configured also has the following parameters used by the program and can be tweaked to determine how they might impact the accuracy and responsiveness of the tracking:
- ping_interval = 12

Given in *seconds*, this parameter determines how often the iPhone is 'pinged' with a UDP message; the original author recommends 12 or shorter
- offline_retries = 7

This parameter specifies the number of times that a phone is pinged, but without a response, before it is declared away.  The higher the retry number, the longer it will take to confirm the phone is really away; conversly a smaller number will result in quicker 'away' declarations, but is likely to trigger false away states.  

As an example, 7 retries at 12 second intervals results in a 1 minute 24 second period until a phone is declared away.

## Please report your experience!
Use the github Issues (https://github.com/toddaustin07/phonepresence/issues) tab for this repository to share your findings.  I'm also interested to see how this works with Android phones.

## SmartThings Integration
An alternate version of this application is available that will allow for full integration with SmartThings.  It requires my bridge server (https://github.com/toddaustin07/edgebridge) and LAN Presence Edge driver available from my [shared projects channel](https://bestow-regional.api.smartthings.com/invite/d429RZv8m9lo).

It also requires **Python 3.7** or later to be on the computer where you will be running the phonetrack application.  If a Windows .exe file is preferred, please contact me and I can provide that.

### phonetrack.cfg
Note that the configuration file for this alternate version contains additional settings.  

- As of 2/14/22, network presence retries are configured **per phone**
- The *bridge_address* value **must** be configured along with the phone IP addresses and names as outlined in the instructions above.  
- The config file also allows for turning on or off console or file logging: simply change the respective configuration line to a 'yes' or 'no'.

### SmartThings device settings
The LAN Presence Edge driver, when installed on your hub, will create a LAN Presence device when an Add device / Scan nearby operation is done in the SmartThings mobile app.  Once that device is created, its device settings must be configured as follows:
- **LAN Device Name**:  this must match the name you used to identify the cellphone IP you specified in the phonetrack.cfg file; avoid blanks and special characters
- **LAN Device Address**:  this must be the IP:port address where the **phonetrack app** is running (*not* the cellphone itself).  For example if you have the phonetrack app running on a computer with IP address 192.168.1.200, then the LAN Device Address you must provide is **192.168.1.200:50001**.  The address must include the port number, which by default is 50001 (but can be changed in the phonetrack.cfg file)
- **Bridge Address**: this must be the IP:port address where the forwarding bridge server is running.  For example if you have the edgebridge app running on a computer with IP address 192.168.1.250, then the Bridge Address you must provide is **192.168.1.250:8088**.  The address must include the port number, which by default is 8088 (but can be changed in an optional edgebridge.cfg file)

### When things get out of synch
There are situations where, often due to a hub reboot (e.g. firmware updates), the accurate presence state of a phone may get 'stuck' to a certain state.  To overcome these cases, periodically there will be a 'forced' update of the phone's most current status to SmartThings (normally updates are only done when a state *change* occurs).  The net result is, if things do get out of synch for whatever reason, they should resolve themselves in about 30 minutes.
