import matplotlib.pyplot as plt
import numpy as np

dirs = "C:/tesis git/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
file = "ZdeW_1234_16-11-24_Control Temp.txt"

data = np.genfromtxt(dirs+file, unpack=True, delimiter=',', skip_header=1)

plt.plot(data[2], data[5])
plt.plot(data[2], data[7])