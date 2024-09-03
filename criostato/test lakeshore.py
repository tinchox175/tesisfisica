#%%
# Example usage
#if __name__ == "__main__":
#    controller = LakeShore340(gpib_address=12)  # Replace with your GPIB address
#    print("Temperature on Channel 1:", controller.read_temperature(channel=1))
#    controller.set_setpoint(295.0, channel=1)
#    print("Setpoint on Channel 1:", controller.get_setpoint(channel=1))
#    controller.close()
#%%
#%%
from ls340 import *
import numpy as np 
controller = LakeShore340(gpib_address=12)
controller.write("RANGE 1, 0")
print(controller.query("RANGE?"))
controller.close()
#controller.write("CRVHDR 60, DT-470, D57330, 2, 500.0, 1")

# %%
config_ls = np.genfromtxt('configls.txt', delimiter=',')
config_ls
np.savetxt('configls.txt', [f'a, b, d, d'], fmt='%s')
# %%
