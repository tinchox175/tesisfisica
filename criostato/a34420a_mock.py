import random
import time
class Agilent34420A:
    """
    A mock driver for the Agilent 34420A Nanovoltmeter.
    This class simulates the instrument's behavior for software testing
    without a physical device connection.
    """
    def __init__(self, resource_string="GPIB0::7::INSTR", range_val=0.1):
        """
        Initializes the mock nanovoltmeter.

        :param resource_string: The VISA resource string (used for logging).
        :param range_val: The initial voltage range in volts.
        """
        # print(f"MOCK: Connecting to Agilent 34420A at {resource_string}")
        self.resource_string = resource_string
        
        # Internal state variables to mimic the device's configuration
        self._range = 0.1
        self._resolution = 1e-7
        self._trigger_source = "IMM"
        self._averaging_state = False
        self._averaging_count = 10

        # Apply initial configuration
        self.configure_device()
        self.set_range(range_val)

    def configure_device(self, voltage_range=0.1, resolution=1e-7):
        """
        Simulates configuring the nanovoltmeter for DC voltage measurement.

        :param voltage_range: Measurement range in volts.
        :param resolution: Measurement resolution in volts.
        """
        # print("MOCK: Resetting instrument to default state.")
        # print(f"MOCK: Configuring for DC Voltage measurement with range={voltage_range} V and resolution={resolution} V.")
        self._range = voltage_range
        self._resolution = resolution

    def set_trigger_source(self, source="IMM"):
        """
        Simulates setting the trigger source.

        :param source: Trigger source (e.g., 'IMM' for immediate, 'EXT' for external).
        """
        # print(f"MOCK: Setting trigger source to {source}.")
        self._trigger_source = source

    def set_averaging(self, state=True, count=10):
        """
        Simulates enabling/disabling measurement averaging.

        :param state: Enable (True) or disable (False) averaging.
        :param count: Number of samples to average if enabled.
        """
        status = 'ON' if state else 'OFF'
        # print(f"MOCK: Setting averaging state to {status}.")
        self._averaging_state = state
        if state:
            # print(f"MOCK: Setting averaging count to {count}.")
            self._averaging_count = count

    def measure_voltage(self):
        """
        Simulates triggering a measurement and returns a plausible voltage reading.
        The value will be a random float within the currently set range.

        :return: Simulated measured voltage in volts.
        """
        # print("MOCK: Reading voltage...")
        # Generate a random voltage within the positive and negative range
        mock_voltage = random.uniform(-float(self._range), float(self._range))
        # print(f"MOCK: Returning simulated value: {mock_voltage:.7f} V")
        return mock_voltage

    def set_resolution(self, resolution):
        """
        Simulates setting the measurement resolution.

        :param resolution: Desired measurement resolution in volts.
        """
        # print(f"MOCK: Setting voltage resolution to {resolution} V.")
        self._resolution = resolution

    def set_range(self, voltage_range):
        """
        Simulates setting the measurement range.

        :param voltage_range: Desired voltage range in volts.
        """
        # print(f"MOCK: Setting voltage range to {voltage_range} V.")
        self._range = voltage_range

    def custom_command(self, command):
        """
        Simulates sending a custom SCPI command to the instrument.

        :param command: SCPI command as a string.
        :return: A mock response if the command is a query, otherwise None.
        """
        if "?" in command:
            # print(f"MOCK: Received custom query: '{command}'. Returning a default value.")
            time.sleep(0.2)
            return 1
        else:
            # print(f"MOCK: Received custom write command: '{command}'.")
            return None

    def close(self):
        """Simulates closing the connection to the instrument."""
        # print(f"MOCK: Closing connection to {self.resource_string}.")
        