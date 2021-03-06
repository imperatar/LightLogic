#!/usr/bin/python

import json
from enum import Enum
import paho.mqtt.client as mqtt


class Device:
	def __init__(self, reference, name = ''):
		self.name = name
		self.reference = reference
	

class Sensor(Device):
	def setActionCallback(self, action_callback):
		self.action_callback = action_callback

	def _process_msg(self, msg_struct):
		self.action_callback

	def on_callback(self, client, userdata, message):
		print(self.name + ": " + str(message.payload.decode("utf-8")) )
		self._process_msg(json.loads(message.payload) )

	def __init__(self, reference, name, mqtt_client):
		Device.__init__(self, reference, name)
		self.action_callback = None
		self.client = mqtt_client
		self.client.subscribe('zigbee2mqtt/' + reference)
		self.client.on_message=self.on_callback


class Output(Device):
	def __init__(self, reference, name, mqtt_client):
		Device.__init__(self, reference, name)
		self.client = mqtt_client
	
	def _set(self, property):
		address = 'zigbee2mqtt/' + self.reference + '/set'
		self.client.publish(address, json.dumps(property) )
		print(self.name + ": " + json.dumps(property))


class Styrbar(Sensor):
	class State(Enum):
		UNDEFINED = 0
		UP = 1
		UP_HOLD = 11
		DOWN = 2
		DOWN_HOLD = 21
		UP_DOWN_RELEASE = 123
		LEFT = 3
		LEFT_HOLD = 31
		LEFT_RELEASE = 32
		RIGHT = 4
		RIGHT_HOLD = 41
		RIGHT_RELEASE = 42
	
	Keys = {
		'':                     State.UNDEFINED,
		'on':                   State.UP,
		'brightness_move_up':   State.UP_HOLD,
		'off':                  State.DOWN,
		'brightness_move_down': State.DOWN_HOLD,
		'brightness_stop':      State.UP_DOWN_RELEASE,
		'arrow_left_click':     State.LEFT,
		'arrow_left_hold':      State.LEFT_HOLD,
		'arrow_left_release':   State.LEFT_RELEASE,
		'arrow_right_click':    State.RIGHT,
		'arrow_right_hold':     State.RIGHT_HOLD,
		'arrow_right_release':  State.RIGHT_RELEASE,
	}

	def __init__(self, reference, name, mqtt_client):
		Sensor.__init__(self, reference, name, mqtt_client)
		self._state = self.State.UNDEFINED
	
	def _process_msg(self, msg_struct):
		if 'action' in msg_struct:
			self._state = self.Keys[msg_struct['action']]
			if self.action_callback is not None:
				self.action_callback(self._state)
		# print(msg_struct)
		# print(self.name + ": " + str(self._state) )

	def getState(self):
		return self._state


class TradfriBulb(Output):
	BRIGHTNESS_MIN = 0
	BRIGHTNESS_MAX = 254

	TEMPERATURE_COLD = 250
	TEMPERATURE_NEUTRAL = 370
	TEMPERATURE_WARM = 454

	class Temp(Enum):
		COOLEST = 0
		COOL = 1
		NEUTRAL = 2
		WARM = 3
		WARMEST = 4
	
	TempKeys = {
		Temp.COOLEST: 'coolest',
		Temp.COOL:    'cool',
		Temp.NEUTRAL: 'neutral',
		Temp.WARM:    'warm',
		Temp.WARMEST: 'warmest'
	}

	def __init__(self, reference, name, mqtt_client):
		Output.__init__(self, reference, name, mqtt_client)
		self.brightness = 0
		self.color_temp = 0

	def set(
		self,
		power = None,
		brightness = None,
		color_hex = None,
		color_rgb = None,
		color_temp = None,
		transition = None,
		brightness_percentage = None,
		color_temp_percentage = None
	):
		out = {}

		if power is not None:
			if power: 
				out['state'] = 'ON'
			else:
				out['state'] = 'OFF'
			
		if brightness is not None:
			out['brightness'] = brightness
			self.brightness = brightness

		if color_hex is not None:
			out['color'] = {'hex': color_hex}

		if color_rgb is not None:
			out['color'] = {'r': color_rgb[0], 'g': color_rgb[1], 'b': color_rgb[2]}

		if color_temp is not None:
			if isinstance(color_temp, int):
				out['color_temp'] = color_temp
				self.color_temp = color_temp
			else:
				out['color_temp'] = self.TempKeys[color_temp]
			
		if transition is not None:
			out['transition'] = transition
			
		if brightness_percentage is not None:
			self.brightness = self.brightness * (brightness_percentage / 100)
			out['brightness'] = self.brightness
			
		if color_temp_percentage is not None:
			self.color_temp = self.color_temp * (color_temp_percentage / 100)
			out['color_temp'] = self.color_temp
		
		self._set(out)
	
	def move(
		self,
		brightness = None,  # int(-254:254), 'stop'
		color_temp = None   # int(), 'stop'
	):
		out = {}
		if brightness is not None:
			out['brightness_move'] = brightness
		if color_temp is not None:
			out['color_temp_move'] = color_temp
		self._set(out)

	def step(
		self,
		brightness = None,  # int(-254:254), 'stop'
		color_temp = None   # int(), 'stop'
	):
		out = {}
		if brightness is not None:
			out['brightness_step'] = brightness
		if color_temp is not None:
			out['color_temp_step'] = color_temp
		self._set(out)


class SonoffMotion(Sensor):
	def __init__(self, reference, name, mqtt_client):
		Sensor.__init__(self, reference, name, mqtt_client)
		self._state = None
	
	def _process_msg(self, msg_struct):
		# print(self.name + ": " + str(msg_struct) )
		if 'occupancy' in msg_struct:
			self._state = msg_struct['occupancy']
			# print(self.name + ": " + str(self._state) )
			if self.action_callback is not None:
				self.action_callback(self._state)

	def getState(self):
		return self._state