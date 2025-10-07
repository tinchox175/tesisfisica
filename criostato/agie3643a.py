import pyvisa

class AgilentE3643A:
    def __init__(self, resource_name='GPIB0::5::INSTR', timeout=5000):
        """
        Initialize the Agilent E3643A Power Supply.
        Connect to the instrument and verify identity.
        """
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(resource_name)
        self.inst.timeout = timeout
        #self.inst.write(f"APPL 2.6,0")
        #self.inst.write(f"OUTP ON")
        
    def close(self):
        """Close the instrument connection."""
        if self.inst is not None:
            self.inst.close()
            self.inst = None
        if self.rm is not None:
            self.rm.close()
            self.rm = None

    def apply(self, voltage):
        """
        Set the output voltage level.
        
        :param voltage: Desired voltage in volts (float).
        """
        if voltage>4.9:
            voltage=4.9
        self.inst.write(f"APPL {voltage},0")
        self.inst.write(f"OUTP ON")

    def set_current(self, current):
        """
        Set the current limit.
        
        :param current: Desired current limit in amperes (float).
        """
        self.inst.write(f"CURR {current}")

    def output_on(self):
        """Turn the output ON."""
        self.inst.write("OUTP ON")

    def output_off(self):
        """Turn the output OFF."""
        self.inst.write("OUTP OFF")

    def measure_voltage(self):
        """
        Measure the output voltage.
        
        :return: Measured voltage (float).
        """
        response = self.inst.query("MEAS:VOLT?")
        return float(response)

    def measure_current(self):
        """
        Measure the output current.
        
        :return: Measured current (float).
        """
        response = self.inst.query("MEAS:CURR?")
        return float(response)

    def get_error(self):
        """
        Retrieve the next error from the error queue.
        
        :return: (error_code, error_message)
        """
        response = self.inst.query("SYST:ERR?")
        # Response format: "+0,\"No error\"" or "+<code>,\"<message>\""
        code_str, msg = response.strip().split(",", 1)
        code = int(code_str)
        msg = msg.strip().strip('"')
        return code, msg
