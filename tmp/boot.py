# This file is executed on every boot (including wake-boot from deepsleep)
import esp
esp.osdebug(True)
#import webrepl
#webrepl.start()


import network
# import ntptime

print('*'*20)
print('Termoreg'.center(20))
print('*'*20)


# 1. Connect to WiFi ##########################
#
import network
import time
try:
    import wificfg
except:
    print('Problem on import file wificfg.py')


if wificfg.modeAP:
    #################################################################### Acces point
    ap = network.WLAN(network.AP_IF) # create access-point interface
    ap.config(**wificfg.AP_Settings) # set the ESSID of the access point
    ap.active(True)         # activate the interface
    time.sleep(0.1)
    print('Access Point interface IP address = {}'.format(ap.ifconfig()[0]))
    #print('Hostname: {}'.format(network.hostname()))

if wificfg.modeSTA:
    # ##############################################################################
    wlan = network.WLAN(network.STA_IF)  # create station interface
    wlan.active(True)  # activate the interface
    if not wlan.isconnected():
        print('connecting to {} network...'.format(wificfg.STA_Settings['ssid']))
        try:
            wlan.connect(wificfg.STA_Settings['ssid'], wificfg.STA_Settings['key'])
            print('Connected to access point {}'.format(wlan.config('essid')))
        except:
            if not wlan.isconnected():
                time.sleep(10)
            pass
    else:
        print('Already connected to access point {}'.format(wlan.config('essid')))
    print('Station interface IP address = {}'.format(wlan.ifconfig()[0]))
    # ##############################################################################
