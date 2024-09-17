import pyvisa

class PowerSupply6684A:
    def __init__(self, address):
        """Initialize the connection to the power supply."""
        self.rm = pyvisa.ResourceManager()
        self.device = self.rm.open_resource(address)
        self.device.timeout = 5000  # Set timeout in milliseconds

    def identify(self):
        """Get device identification."""
        return self.device.query('*IDN?')

    def set_voltage(self, voltage):
        """Set the output voltage."""
        self.device.write(f'VOLT {voltage}')

    def get_voltage(self):
        """Read the set voltage value."""
        return float(self.device.query('VOLT?'))

    def set_current(self, current):
        """Set the output current limit."""
        self.device.write(f'CURR {current}')

    def get_current(self):
        """Read the set current value."""
        return float(self.device.query('CURR?'))

    def output_on(self):
        """Enable the power supply output."""
        self.device.write('OUTP ON')

    def output_off(self):
        """Disable the power supply output."""
        self.device.write('OUTP OFF')

    def get_output_state(self):
        """Check if the output is ON or OFF."""
        return bool(int(self.device.query('OUTP?')))

    def close(self):
        """Close the connection to the device."""
        self.device.close()

# Example usage
if __name__ == "__main__":
    psu = PowerSupply6684A('GPIB::5::INSTR')  # Update with your GPIB address
    print(psu.identify())

    psu.set_voltage(10.0)
    print(f"Set Voltage: {psu.get_voltage()} V")

    psu.set_current(2.0)
    print(f"Set Current: {psu.get_current()} A")

    psu.output_on()
    print(f"Output State: {psu.get_output_state()}")  # Should return True

    psu.output_off()
    print(f"Output State: {psu.get_output_state()}")  # Should return False

    psu.close()