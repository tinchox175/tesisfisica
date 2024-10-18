import pyvisa

class hp34970:
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource('GPIB0::9::INSTR')
        self.instrument.write_termination = '\n'
        self.instrument.read_termination = '\n'

    def open_channels(self, channel_list):
        """
        Opens (disconnects) the specified channels.
        """
        if isinstance(channel_list, (list, tuple)):
            channel_str = ','.join(str(ch) for ch in channel_list)
        else:
            channel_str = str(channel_list)
        command = f'ROUTe:OPEN (@{channel_str})'
        self.instrument.write(command)
        print(f"Opened channels: {channel_str}")

    def close_channels(self, channel_list):
        """
        Closes (connects) the specified channels.
        """
        if isinstance(channel_list, (list, tuple)):
            channel_str = ','.join(str(ch) for ch in channel_list)
        else:
            channel_str = str(channel_list)
        command = f'ROUTe:CLOSe (@{channel_str})'
        self.instrument.write(command)
        print(f"Closed channels: {channel_str}")

    def is_channel_open(self, instrument, channel):
        """
        Returns True if the channel is open, False if closed.
        """
        response = self.instrument.query(f'ROUTe:OPEN? (@{channel})').strip()
        return response == '1'

