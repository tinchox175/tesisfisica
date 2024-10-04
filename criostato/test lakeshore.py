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
target_setpoint=293
rate=-2
t0 = time.time()
t = 0
controller = LakeShore340(gpib_address=12)
current_setpoint = controller.get_setpoint()
rampa = np.arange(float(295), float(target_setpoint), float(rate)/30)
rampa[-1] = target_setpoint
print(rampa)
for i in rampa:
        controller.set_setpoint(np.round(i,4))
        time.sleep(2)
        t = time.time()-t0
        print(t)


#%%

print(np.arange(295, 280, -2))