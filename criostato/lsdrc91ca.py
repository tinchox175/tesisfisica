import pyvisa

class LakeShoreDRC91CA:
    def __init__(self, resource_name="GPIB0::12::INSTR", timeout=2000):
        """
        Initialize the Lake Shore DRC-91CA instrument connection.
        """
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(resource_name)
        self.inst.timeout = timeout
        
    def close(self):
        """Close the connection to the instrument."""
        if self.inst is not None:
            self.inst.close()
            self.inst = None
        if self.rm is not None:
            self.rm.close()
            self.rm = None
            
    def read_temperature(self):
        """
        Query the current temperature from a given channel (if applicable).
        """
        cmd = f"WS"
        response = self.inst.query(cmd)
        return float(response.split('\r')[0].split('K')[0])
            
    def set_setpoint(self, setpoint):
        """
        Set the temperature setpoint on the instrument.
        """
        cmd = f"S{float(setpoint)}"
        self.inst.write(cmd)
    
    def get_setpoint(self):
        """
        Query the currently programmed setpoint.
        """
        response = self.inst.query("WP")
        return float(response.split('\r')[0].split('K')[0])
    
    def set_heater_range(self, range_value):
        """
        Set the heater range (if applicable).
        """
        cmd = f"R{range_value}"
        self.inst.write(cmd)
    
    def get_HTR(self):
        """
        Set the heater range (if applicable).
        """
        cmd = f"W3"
        response = self.inst.query(cmd)
        return float(response.split('\r')[0].split(',')[-1])