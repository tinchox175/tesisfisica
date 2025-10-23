import random
import time

class LakeShoreDRC91CA:
    """
    A mock driver for the Lake Shore DRC-91CA Temperature Controller.
    This class simulates the instrument's behavior for software testing
    without a physical device connection.
    """
    def __init__(self, resource_name="GPIB0::12::INSTR", timeout=2000):
        """
        Initializes the mock temperature controller.

        :param resource_name: The VISA resource string (used for logging).
        :param timeout: The communication timeout (ignored in mock).
        """
        print(f"MOCK: Connecting to Lake Shore DRC-91CA at {resource_name}")
        self.resource_name = resource_name
        
        # Internal state variables
        self._setpoint = 300.0  # Default to room temperature (Kelvin)
        self._temperature = 300.1 # Start slightly off from setpoint
        self._heater_range = 0

    def close(self):
        """Simulates closing the connection to the instrument."""
        print(f"MOCK: Closing connection to {self.resource_name}.")

    def read_temperature(self):
        """
        Simulates reading the current temperature.
        The temperature will slowly move towards the setpoint with some noise.
        """
        # print("MOCK: Reading temperature...")
        # Simulate the temperature moving 10% closer to the setpoint each read
        diff = self._setpoint - self._temperature
        self._temperature += diff * 0.05
        # Add a small amount of random noise
        self._temperature += (random.random() - 0.5) * 0.05
        
        return self._temperature
        # return 300

    def set_setpoint(self, setpoint):
        """
        Simulates setting the temperature setpoint.
        """
        setpoint_float = float(setpoint)
        print(f"MOCK: Setting setpoint to {setpoint_float} K.")
        self._setpoint = setpoint_float

    def get_setpoint(self):
        """
        Simulates querying the currently programmed setpoint.
        """
        print(f"MOCK: Querying setpoint. Returning {self._setpoint} K.")
        return self._setpoint

    def set_heater_range(self, range_value):
        """
        Simulates setting the heater range.
        The DRC-91CA has ranges 0-5.
        """
        range_int = int(range_value)
        if not 0 <= range_int <= 5:
            print(f"MOCK WARNING: Heater range {range_int} is outside the typical 0-5 range.")
        
        print(f"MOCK: Setting heater range to {range_int}.")
        self._heater_range = range_int

    def get_HTR(self):
        """
        Simulates reading the heater output percentage.
        The output is proportional to the difference between setpoint and current temp.
        """
        print("MOCK: Querying heater output (HTR)...")
        temp_diff = self._setpoint - self._temperature
        
        # Simple proportional control simulation
        if temp_diff > 0:
            # Heater is on if current temp is below setpoint
            # Power increases the further away we are, capped at 100%
            heater_output = min(100.0, temp_diff * 15) # Scaled for plausible values
        else:
            # Heater is off if we are at or above the setpoint
            heater_output = 0.0

        # Add a tiny bit of noise to the output reading
        heater_output += (random.random() - 0.5) * 0.2
        # Clamp the value between 0 and 100
        heater_output = max(0, min(100, heater_output))

        return heater_output
