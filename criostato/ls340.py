#%%
import pyvisa

class LakeShore340:
    def __init__(self, gpib_address=12):
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(f'GPIB::{gpib_address}::INSTR')
        self.instrument.timeout = 5000  # Set timeout in milliseconds

    def query(self, command):
        """Send a query to the instrument and return the response."""
        try:
            response = self.instrument.query(command)
            return response.strip()
        except Exception as e:
            print(f"Error querying the instrument: {e}")
            return None

    def write(self, command):
        """Send a command to the instrument."""
        try:
            self.instrument.write(command)
        except Exception as e:
            print(f"Error writing to the instrument: {e}")

    def read_temperature(self, channel='A'):
        """Read the temperature from the specified channel (1 or 2)."""
        command = f'KRDG? {channel}'
        return self.query(command)

    def set_setpoint(self, setpoint, channel='A'):
        """Set the temperature setpoint for the specified channel (1 or 2)."""
        command = f'SETP {channel},{setpoint}'
        self.write(command)

    def get_setpoint(self, channel='A'):
        """Get the temperature setpoint for the specified channel (1 or 2)."""
        command = f'SETP? {channel}'
        return self.query(command)

    def set_pid(self, p, i, d):
        """Set PID parameters."""
        command = f'PID {p}, {i}, {d}'
        return self.query(command)
    
    def analog_out(self, v):
        command = f'ANALOG 1, 0, 2,,,,, {v}'
        return self.write(command)
    
    def analog_read(self):
        command = f'AOUT? 1'
        return self.query(command)
    
    def close(self):
        """Close the connection to the instrument."""
        self.instrument.close()

# %%
