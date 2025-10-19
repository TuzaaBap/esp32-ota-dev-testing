from machine import Pin
import time
try:
    led = Pin("LED", Pin.OUT)
except:
    led = Pin(21, Pin.OUT)
while True:
    led.on();  time.sleep(0.5)
    led.off(); time.sleep(0.5)