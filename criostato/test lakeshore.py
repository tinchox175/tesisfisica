#%%
# Example usage
#if __name__ == "__main__":
#    cont[roller = LakeShore340(gpib_address=12)  # Replace with your GPIB address
#    print("Temperature on Channel 1:", controller.read_temperature(channel=1))
#    controller.set_setpoint(295.0, channel=1)
#    print("Setpoint on Channel 1:", controller.get_setpoint(channel=1))
#    controller.close()
#%%
#%%
from ls340 import *
import k224
import pymeasure.instruments.agilent as agi # type: ignore
import numpy as np 
import time

t, r = np.loadtxt('C:/tesis git/tesisfisica/Termometros/Patrones/GC11-C19522/C19522.dat', skiprows=3, unpack=True)

# %%
ls = LakeShore340(12)
ls.write('CRVHDR 59, C19522, 403501, 3, 334.0, 1')
for i in np.arange(0,len(t)):
    ls.write(f'CRVPT 59, {i}, {np.round(r[i],3)}, {np.round(t[i],3)}')
    ls.write('CRVSAV')

# %%
