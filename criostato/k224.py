# -*- coding: utf-8 -*-
"""
Created on Wed Aug 28 14:32:52 2024

@author: Administrator
"""

import pyvisa
import enum

class Readout_Values:
    def __init__(self):
        self.raw = ""
        self.current = 0.0
        self.overcompliance = False
        self.voltage = 0.0
        self.time = 0.0

# Range Commands
RANGE_LIST = (
    'R0',
    'R5',
    'R6',
    'R7',
    'R8',
    'R9',
    )

def get_available_devices():
    rm = pyvisa.ResourceManager()
    devices = rm.list_resources()
    return devices

def _decode_values(rawdata):
    splitted = rawdata.split(',')
    readout = Readout_Values()
    readout.raw = rawdata
    for element in splitted:
        if 'DCI' in element:
            if element[0] == 'O':
                readout.overcompliance = True
            readout.current = float(element[4:])
        if 'V' in element:
            readout.voltage = float(element[1:])
        if 'W' in element:
            readout.time = float(element[1:])
    return readout

def _format_e(n):
    a = '%E' % n
    return a.split('E')[0].rstrip('0').rstrip('.') + 'E' + a.split('E')[1]

class KEITHLEY_224(object):

    class Ranges(enum.Enum):
        AUTO = 0
        MAN_20uA = 1
        MAN_200uA = 2
        MAN_2mA = 3
        MAN_20mA = 4
        MAN_1m01A = 5

    def __init__(self, address="GPIB0::2::INSTR"):
        self._address = address
        self._rm = pyvisa.ResourceManager()
        self._inst = self._rm.open_resource(address)
        self._range = self.Ranges.AUTO
        self.time = 0.05
        self.operate = False

    def __del__(self):
        self.operate = False

    def get_measurement(self):
        self._inst.timeout = 1000
        result = _decode_values(self._inst.read())
        return result

    @property
    def range(self):
        return self._range

    @range.setter
    def range(self, range):
        if not isinstance(range, self.Ranges):
            raise TypeError('mode must be an instance of Ranges Enum')
        self._range = range
        self._inst.write(RANGE_LIST[self._range.value]+'X')

    @property
    def voltage(self):
        return self._voltage

    @voltage.setter
    def voltage(self, voltage):
        if (voltage < 1):
            self._voltage = voltage
            self._inst.write('V'+ '1'+'X')
        elif (voltage > 10):
            self._voltage = voltage
            self._inst.write('V'+ '10'+'X')
        self._voltage = voltage
        self._inst.write('V'+ _format_e(voltage)+'X')

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, current):
        if (current < -0.11):
            self._current = current
            self._inst.write('I' + '-0.10' + 'X')
        elif (current > 0.011):
            self._current = current
            self._inst.write('I' + '0.010' + 'X')
        else:
            self._current = current
            self._inst.write('I' + _format_e(current) + 'X')

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, time):
        if (time < 0.05) or (time > 0.9999):
            raise ValueError('time limits: 0.05 to 0.9999 sec')
        self._time = time
        self._inst.write('W' + _format_e(time) + 'X')

    @property
    def operate(self):
        return self._operate

    @operate.setter
    def operate(self, operate):
        if type(operate) != type(True):
            raise ValueError('operate takes a bool value')
        self._operate = operate
        if operate == True:
            self._inst.write('F1X')
        else:
            self._inst.write('F0X')