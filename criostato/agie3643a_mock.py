import random

class AgilentE3643A:
    """
    A mock driver for the Agilent E3643A Power Supply.
    This class simulates the instrument's behavior for software testing
    without a physical device connection.
    """
    def __init__(self, resource_name='GPIB0::5::INSTR', timeout=5000):
        """
        Initializes the mock power supply.

        :param resource_name: The VISA resource string (used for logging).
        :param timeout: The communication timeout (ignored in mock).
        """
        print(f"MOCK: Connecting to Agilent E3643A at {resource_name}")
        self.resource_name = resource_name
        
        # Internal state variables
        self._voltage_setpoint = 0.0
        self._current_limit = 0.0
        self._output_on = False

    def close(self):
        """Simulates closing the instrument connection."""
        print(f"MOCK: Closing connection to {self.resource_name}.")
        self._output_on = False

    def apply(self, voltage):
        """
        Simulates setting the output voltage level and enabling the output.

        :param voltage: Desired voltage in volts (float).
        """
        applied_voltage = float(voltage)
        if applied_voltage > 4.9:
            print(f"MOCK WARNING: Voltage {applied_voltage}V is > 4.9V. Capping at 4.9V.")
            applied_voltage = 4.9
        
        print(f"MOCK: Applying {applied_voltage}V and turning output ON.")
        self._voltage_setpoint = applied_voltage
        self.output_on()

    def set_current(self, current):
        """
        Simulates setting the current limit.

        :param current: Desired current limit in amperes (float).
        """
        current_limit = float(current)
        print(f"MOCK: Setting current limit to {current_limit} A.")
        self._current_limit = current_limit

    def output_on(self):
        """Simulates turning the output ON."""
        print("MOCK: Output ON.")
        self._output_on = True

    def output_off(self):
        """Simulates turning the output OFF."""
        print("MOCK: Output OFF.")
        self._output_on = False

    def measure_voltage(self):
        """
        Simulates measuring the output voltage.

        :return: Measured voltage (float).
        """
        print("MOCK: Measuring voltage...")
        if self._output_on:
            # Simulate small noise around the setpoint
            noise = (random.random() - 0.5) * 0.01 * self._voltage_setpoint
            measured_voltage = self._voltage_setpoint + noise
            return measured_voltage
        else:
            # When output is off, voltage should be near zero
            return random.random() * 1e-4

    def measure_current(self):
        """
        Simulates measuring the output current.

        :return: Measured current (float).
        """
        print("MOCK: Measuring current...")
        if self._output_on:
            # Simulate a current draw, e.g., 25% of the set voltage,
            # but never exceeding the current limit.
            # Add some noise as well.
            simulated_draw = self._voltage_setpoint * 0.25 
            noise = (random.random() - 0.5) * 0.02
            
            # The actual current is the lesser of the simulated draw or the limit
            actual_current = min(simulated_draw, self._current_limit) + noise
            # Ensure current is not negative due to noise
            return max(0, actual_current)
        else:
            # When output is off, current should be near zero
            return random.random() * 1e-5

    def get_error(self):
        """
        Simulates retrieving an error from the error queue.

        :return: (0, "No error")
        """
        print("MOCK: Querying error queue.")
        return 0, "No error"