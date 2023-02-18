#
# user_config.py
#
# Used by mbus_master_hat_mqtt.py
#
# Copyright (C) 2020 packom.net Limited
#

#
# Stuff you'll definitely want to change
#

# Address or hostname of MQTT broker
mqtt_addr = 'mosquitto'

# Username and password of MQTT broker
mqtt_username = 'username'
mqtt_password = 'password'


# Primary address of M-Bus slave to read
slave_address = 48

#
# Stuff you might want to change
#

# MQTT broker port (1883 is the default)
mqtt_port = 1883

# Baud rate of the M-Bus slave
baud_rate = 2400

# MQTT topic for this script to listen for
subscribe_topic = '/mbus'

# MQTT message which causes this script to query the slave
read_command = 'read'

# MQTT topic to use to post results
post_topic = '/mbus_value'

#
# Stuff you probably don't want to change
#

# Time to sleep between checks that we're still connected to the MQTT broker
sleep_time = 60

# GPIO number to turn M-Bus power on
# Broadcom pin number, not wiringPi or physical pin
mbus_gpio_bcm = 26  

# Serial device to use to control the M-Bus Master Hat
serial_dev = '/dev/ttyAMA0'

# Name of this script used for logging purposes
script_name = 'mbus_master_hat_mqtt'
