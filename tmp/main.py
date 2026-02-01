from machine import Pin, I2C
from utime import sleep

from htu21d import HTU21D, HTU21DConfiguration

i2c0_sda = Pin(5)
i2c0_scl = Pin(4)
i2c0 = I2C(0, sda=i2c0_sda, scl=i2c0_scl)

htu21d = HTU21D(0x40, i2c0)

while True:
    measurements = htu21d.measurements
    print(f"Temperature: {measurements['t']} °C, humidity: {measurements['h']} %RH")
    sleep(5)