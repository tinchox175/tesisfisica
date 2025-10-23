import enum
import random
import time as a_time # aliased to avoid conflict with the 'time' property

class Readout_Values:
    """A class to hold the decoded measurement values."""
    def __init__(self):
        self.raw = ""
        self.current = 0.0
        self.overcompliance = False
        self.voltage = 0.0
        self.time = 0.0

    def __str__(self):
        return (f"Raw: {self.raw}\n"
                f"Current: {self.current} A\n"
                f"Voltage: {self.voltage} V\n"
                f"Overcompliance: {self.overcompliance}\n"
                f"Timestamp: {self.time}")

# --- Helper Functions ---

def _decode_values(rawdata):
    """Decodes the raw string data from the device into Readout_Values."""
    splitted = rawdata.split(',')
    readout = Readout_Values()
    readout.raw = rawdata
    for element in splitted:
        if 'DCI' in element:
            if element.startswith('O'):
                readout.overcompliance = True
            readout.current = float(element[4:])
        if 'V' in element and not 'DCI' in element:
            readout.voltage = float(element[1:])
        if 'W' in element:
            readout.time = float(element[1:])
    return readout

def _format_e(n):
    """Formats a number in scientific notation as the device expects."""
    a = '%E' % n
    return a.split('E')[0].rstrip('0').rstrip('.') + 'E' + a.split('E')[1]

def get_available_devices():
    """Returns a list of mock VISA device addresses."""
    print("MOCK: Searching for devices...")
    return ["GPIB0::2::INSTR", "GPIB0::22::INSTR", "ASRL1::INSTR"]

# --- Main Driver Class ---

class KEITHLEY_224(object):
    """
    A mock driver for the Keithley 224 Current Source.
    This class simulates the behavior of the real driver without
    requiring a physical connection to the instrument.
    """

    class Ranges(enum.Enum):
        AUTO = 0
        MAN_20uA = 1
        MAN_200uA = 2
        MAN_2mA = 3
        MAN_20mA = 4
        MAN_100mA = 5 # Corrected from 1m01A for clarity

    def __init__(self, address="GPIB0::2::INSTR"):
        print(f"MOCK: Connecting to Keithley 224 at {address}")
        self._address = address
        self._range = self.Ranges.AUTO
        self._time = 0.05
        self._operate = False
        self._voltage = 1.0 # Default compliance voltage
        self._current = 0.0 # Default output current

    def __del__(self):
        print("MOCK: Disconnecting from Keithley 224.")
        self.operate = False

    def get_measurement(self):
        """
        Returns a simulated measurement result.
        The returned current will be close to the set current with some noise.
        """
        print("MOCK: Reading measurement...")
        # Simulate some measurement noise
        noise = self._current * 0.01 * (random.random() - 0.5)
        measured_current = self._current + noise
        
        # Build the raw data string that the real device would send
        mock_raw_data = (f"NDCI{_format_e(measured_current)},"
                         f"V{_format_e(self._voltage)},"
                         f"W{a_time.time()}")
                         
        result = _decode_values(mock_raw_data)
        return result

    @property
    def range(self):
        return self._range

    @range.setter
    def range(self, range_enum):
        if not isinstance(range_enum, self.Ranges):
            raise TypeError('mode must be an instance of Ranges Enum')
        # print(f"MOCK: Setting range to {range_enum.name}")
        self._range = range_enum

    @property
    def voltage(self):
        return self._voltage

    @voltage.setter
    def voltage(self, voltage):
        # The original logic had some quirks, this is a simplified version
        if not 1 <= voltage <= 10:
             print(f"MOCK WARNING: Voltage {voltage} is outside typical 1-10V range.")
        
        # print(f"MOCK: Setting compliance voltage to {voltage} V")
        self._voltage = voltage


    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, current):
        # The original logic had some quirks, this is a simplified version
        if not -0.105 <= current <= 0.105:
            # raise ValueError("Current must be between -0.105 and 0.105 A")
            print(f"MOCK WARNING: Current {current}A is outside typical -0.105 to 0.105A range.")
            current = max(min(current, 0.105), -0.105)
        # print(f"MOCK: Setting current to {current} A")
        self._current = current

    @property
    def time(self):
        return self._time

    @time.setter
    def time(self, time_val):
        if not 0.05 <= time_val <= 0.9999:
            # raise ValueError('Time limits: 0.05 to 0.9999 sec')
            print(f"MOCK WARNING: Time {time_val}s is outside typical 0.05-0.9999s range.")
            time_val = max(min(time_val, 0.9999), 0.05)
        # print(f"MOCK: Setting time parameter to {time_val} s")
        self._time = time_val

    @property
    def operate(self):
        return self._operate

    @operate.setter
    def operate(self, operate_bool):
        if not isinstance(operate_bool, bool):
            raise ValueError('operate takes a boolean value (True/False)')
        
        # print(f"MOCK: Setting OPERATE state to {operate_bool}")
        self._operate = operate_bool
