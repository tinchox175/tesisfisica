import pyvisa

class Agilent34420A:
    def __init__(self, resource_string="GPIB0::7::INSTR", range=0.1):
        self.resource_string = resource_string
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(self.resource_string)
        self.configure_device()
        self.set_range(range)
        
    def configure_device(self, voltage_range=0.1, resolution=1e-7):
        """
        Configures the nanovoltmeter for DC voltage measurement.
        
        :param voltage_range: Measurement range in volts.
        :param resolution: Measurement resolution in volts.
        """
        self.instrument.write("*RST")  # Reset to known state
        config_command = f"CONF:VOLT:DC {voltage_range},{resolution}"
        self.instrument.write(config_command)
        #self.set_trigger_source("IMM")  # Immediate trigger by default
    
    def set_trigger_source(self, source="IMM"):
        """
        Sets the trigger source.
        
        :param source: Trigger source (e.g., 'IMM' for immediate, 'EXT' for external).
        """
        self.instrument.write(f"TRIG:SOUR {source}")
    
    def set_averaging(self, state=True, count=10):
        """
        Enables or disables measurement averaging and sets the count.
        
        :param state: Enable (True) or disable (False) averaging.
        :param count: Number of samples to average if enabled.
        """
        self.instrument.write(f"VOLT:DC:AVER:STAT {'ON' if state else 'OFF'}")
        if state:
            self.instrument.write(f"VOLT:DC:AVER:COUN {count}")
    
    def measure_voltage(self):
        """
        Triggers a measurement and returns the voltage reading.
        
        :return: Measured voltage in volts.
        """
        #self.instrument.write("INIT")
        voltage = self.instrument.query("READ?")
        return float(voltage)
    
    def set_resolution(self, resolution):
        """
        Sets the measurement resolution.
        
        :param resolution: Desired measurement resolution in volts.
        """
        self.instrument.write(f"VOLT:DC:RES {resolution}")
    
    def set_range(self, voltage_range):
        """
        Sets the measurement range.
        
        :param voltage_range: Desired voltage range in volts.
        """
        self.instrument.write(f"VOLT:DC:RANG {voltage_range}")
    
    def custom_command(self, command):
        """
        Sends a custom SCPI command to the instrument.
        
        :param command: SCPI command as a string.
        :return: Response from the instrument, if any.
        """
        return self.instrument.query(command) if "?" in command else self.instrument.write(command)
    
    #def close(self):
    #    """Closes the connection to the instrument."""
    #    self.instrument.close()
    #    self.rm.close()

# Example usage in a larger script
#if __name__ == "__main__":
#    # Initialize the nanovoltmeter
#    nanovoltmeter = Agilent34420A("GPIB0::22::INSTR")
#    
#    try:
#        # Set averaging with a count of 5 samples
##        nanovoltmeter.set_averaging(state=True, count=5)
  #      
   #     # Set trigger source to manual for controlled triggering
    ##   
#        # Set a custom measurement range and resolution
 #       nanovoltmeter.set_range(0.1)
  #      nanovoltmeter.set_resolution(1e-8)
   #     
    #    # Perform a series of measurements
     #   for i in range(3):
      #      voltage = nanovoltmeter.measure_voltage()
       #     print(f"Measurement {i+1}: {voltage} V")
#        
 #       # Send a custom SCPI command (e.g., check the device ID)
  #      idn_response = nanovoltmeter.custom_command("*IDN?")
   #     print(f"Instrument ID: {idn_response}")
    #
    #finally:
     #   # Ensure the instrument connection is closed
      #  nanovoltmeter.close()
