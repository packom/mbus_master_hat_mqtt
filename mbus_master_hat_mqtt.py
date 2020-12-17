#!/usr/bin/python
#
# mbus_master_hat_mqtt.py
#
# Sample app to expose M-Bus Master Hat functionality over MQTT
#
# Copyright (C) 2020 packom.net Limited
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of  MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# To install pre-requisite python modules:
#
# sudo apt install python-pip
# git clone https://github.com/ganehag/pyMeterBus
# cd pyMeterBus && sudo python setup.py install && cd ..
# sudo pip install paho-mqtt
#

#
# What this script does/how it works:
#
# The main method:
# - Register a signal handler to catch Ctrl-C
# - Check we have an M-Bus Master Hat installed
# - Connect to MQTT broker (and turns on the M-Bus power when connected)
# - Loop forever, periodically checking for an MQTT connection
#
# The on_connect method received MQTT messages using the subscribe_topic
# (which can be set in user_config.py).  If it gets a message then
# it checks whether the payload is read_command (again set in user_config.py).
# If it is, it queries the M-Bus slave at address slave_address (set in
# user_config.py).  If it gets a response it looks like the manufacturer
# value and sends it out via MQTT using the post_topic (user_config.py).
#
# To exit, hit Ctrl-C - the bus powers off automatically
#
# With the default config, send the following MQTT topic and payload
# to cause the script to query slave at address 48:
#    /mbus read
#
# Using an ATS water meter the script sends:
#    /mbus_value manufacturer ATS
#
# It is of course possible your M-Bus device doesn't support the manufacturer
# value, and has a different address than 48!
#

import sys, time, datetime, os, serial, meterbus, json
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
from signal import signal, SIGINT
from user_config import *

mbus_master_products = ['M-Bus Master', 'M-Bus Master DS']

# Basic logging method
def log(to_log):
  print(script_name + ": " + to_log)
  sys.stdout.flush()

# Signal handler
def handler(signal_received, frame):
  log("Ctrl-C caught")
  quit(0)

# Main routine - see comment above for behaviour
def main():  
  global power_on, connected
  log("starting")

  power_on = False
  connected = False

  signal(SIGINT, handler)

  mbus_hat_check()
  mqtt_connect()
  main_loop()

# Simple routine to turn off bus power and then exit
def quit(rc):
  global power_on
  if power_on:
    mbus_power_off()
  log("exiting")
  exit(rc)

# Check we have an M-Bus Master Hat installed
def mbus_hat_check():
  got_hat = False
  if os.path.isfile('/proc/device-tree/hat/product'):
    namef = open('/proc/device-tree/hat/product')
    if namef.read().replace('\x00', '') in mbus_master_products:
      log('Found packom.net M-Bus Master Hat')
      log(' Type: ' + open('/proc/device-tree/hat/product').read())
      log(' Version: ' + open('/proc/device-tree/hat/product_ver').read())
      got_hat = True
  if got_hat == False:
    log('No M-Bus Master Hat found (did you reboot after installing?)')
    quit(1)

# Connect to the MQTT broker - this is done asynchronously.  Once connected
# on_connect is called

def mqtt_connect():
  global client, connected
  client = mqtt.Client(protocol=mqtt.MQTTv31)
  client.on_connect = on_connect
  client.on_message = on_message
  client.on_disconnect = on_disconnect
  connected = False
  client.connect_async(mqtt_addr, mqtt_port, 60)
  client.loop_start()

# Triggered when connected to the MQTT broker - turns M-Bus power on
def on_connect(client, userdata, flags, rc):
  global connected
  log("Connected to MQTT broker with result code " + str(rc))

  # Subscribing in on_connect() means that if we lose the connection and
  # reconnect then subscriptions will be renewed.
  client.subscribe(subscribe_topic)
  log("Subcribed to topic: " + subscribe_topic)
  connected = True

  mbus_power_on()

# Triggered when disconnected from the MQTT broker
def on_disconnect(client, userdata, rc):
  global connected, run
  log("Disconnected from broker")
  connected = False
  run = False  

# Query the M-Bus
def on_message(client, userdata, msg):
  print msg
  if msg.payload.startswith(read_command):
    mbus_query()
  else:
    client.publish(post_topic, "unknown command")
   
# Turns M-Bus power on
def mbus_power_on():
  global power_on
  GPIO.setwarnings(False)
  GPIO.setmode(GPIO.BCM)
  GPIO.setup(mbus_gpio_bcm, GPIO.OUT)  # Strictly this is unnecessary, but belt and braces
  GPIO.output(mbus_gpio_bcm, GPIO.HIGH)
  power_on = True

# Turns M-Bus power off
def mbus_power_off():
  GPIO.output(mbus_gpio_bcm, GPIO.LOW)
  GPIO.cleanup()
  power_on = False

# Actually sends an M-Bus query out
def mbus_query():
  ser = serial.Serial(serial_dev, baud_rate, 8, 'E', 1, 0.5)
  try:
    meterbus.send_ping_frame(ser, slave_address)
    frame = meterbus.load(meterbus.recv_frame(ser, 1))
    assert isinstance(frame, meterbus.TelegramACK)
    meterbus.send_request_frame(ser, slave_address)
    frame = meterbus.load(meterbus.recv_frame(ser, meterbus.FRAME_DATA_LENGTH))
    assert isinstance(frame, meterbus.TelegramLong)
    mbus_json = json.loads(frame.to_JSON())
    manufacturer = mbus_json["body"]["header"]["manufacturer"]
    client.publish(post_topic, "manufacturer " + manufacturer)
  except:
    log('Failed to read data from slave at address %d' % slave_address)
    client.publish(post_topic, "failed")

# Loops, exiting if disconnected from the MQTT broker
def main_loop():
  global connected, run
  run = True
  while run:
    time.sleep(sleep_time)
    if not connected:
      run = False
      break

  log("Not connected to MQTT broker")
  quit(0)
  
if __name__ == "__main__":
  main()

