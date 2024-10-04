import pyvisa

class Lakeshore625:
    def __init__(self, n = 11):
        """Initialize communication with the Lake Shore 625 power supply.

        Parameters:
        resource_name (str): VISA resource name (e.g., 'GPIB0::25::INSTR').
        """
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(f'GPIB0::{n}::INSTR')

    def close(self):
        """Close the connection to the instrument."""
        self.inst.close()
        self.rm.close()

    def write(self, cmd):
        """Send a command to the instrument."""
        self.inst.write(cmd)

    def query(self, cmd):
        """Send a query to the instrument and return the response."""
        return self.inst.query(cmd)
    
    def status(self):
        return float(self.query('*OPC?'))

    def limit(self, current, voltage, rate):
        """Set the limits for current, voltage and rate.

        Parameters:
        current (float), voltage (float), rate (float)
        """
        self.write(f'LIMIT {current}, {voltage}, {rate}')
        
    def set_current(self, current):
        """Set the output current in Amperes.

        Parameters:
        current (float): Desired current in Amperes.
        """
        self.write(f'SETI {current}')

    def get_current(self):
        """Get the actual output current in Amperes."""
        return float(self.query('RDGI?'))

    def get_current_psh(self):
        return float(self.query('PSHIS?'))

    def set_voltage(self, voltage):
        """Set the output voltage in Volts.

        Parameters:
        voltage (float): Desired voltage in Volts.
        """
        self.write(f'SETV {voltage}')

    def get_voltage(self):
        """Get the actual output voltage in Volts."""
        return float(self.query('RDGV?'))
    
    def get_voltage_sense(self):
        """Get the actual output voltage in Volts."""
        return float(self.query('RDGRV?'))

    def psh(self, mode):
        """Turn on/off persitent heating switch"""
        self.write('PSH {mode}')

    def output_on(self):
        """Turn the output on."""
        self.write('OPON')

    def output_off(self):
        """Turn the output off."""
        self.write('OPOF')

    def set_ramp_rate(self, rate):
        """Set the ramp rate in Amperes per second.

        Parameters:
        rate (float): Desired ramp rate in A/s.
        """
        self.write(f'RATE {rate}')

    def get_ramp_rate(self):
        """Get the current ramp rate in Amperes per second."""
        return float(self.query('RATE?'))

    def get_status_ramp(self):
        """Get the current status of the power supply ramp."""
        self.write('OPSTE 010')
        return float(self.query('OPSTR?'))
    
    def get_status_switch(self):
        """Get the current status of the power supply switching."""
        self.write('OPSTE 001')
        return float(self.query('OPSTR?'))
#%%
# Example usage:
#if __name__ == '__main__':
#    # Replace 'GPIB0::25::INSTR' with your actual resource name
#    psu = Lakeshore625('GPIB0::11::INSTR')
#    try:
#        psu.set_current(0.0001)           # Set current to 5 A
#        current = psu.get_current()
#        print(f"Current output: {current} A")
#        psu.output_on()                # Turn on the output
#    finally:
#        psu.close()                    # Ensure the connection is closed
