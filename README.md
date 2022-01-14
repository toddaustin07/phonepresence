# phonetrack application

This Python script uses a technique, borrowed from here => https://github.com/mudape/iphonedetect, to track presence of iPhones on the home network.  On a periodic basis (every 12 seconds, for example) it sends a UDP message to port 5353 (mDNS) of the mobile phone's IP address to try and force the phone to renew its existance on local network address tables.  The script then examines the local ARP table (via IP commands) to see if the phone's ip address is included.  If it is, it is presumed present. If it is not, a number of subsequent retries are attempted (e.g. 5-10) before declaring the phone not present.  

## Known Issues
With the latest iOS (version 15), this technique has proven unreliable.  A large number of retries (perhaps 10) is required to ensure false away-states are not reported, which can take up to 2 minutes or more.  More critically, upon arrival of an iPhone that is asleep, detection may not occur until the iPhone is woken up by the user.

The above is *my* personal experience running this test app on a Raspberry Pi 4 with Raspbian OS (Linux kernal 5.10.17-v7l+) and with iPhone 12s with iOS 15.1.1.  However, others should try this to see if their results are similar.

## Try it yourself

- Download phonetrack.py and phonetrack.cfg onto a computer (Linux, Windows, Mac) with Python 3.7 or later.
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
