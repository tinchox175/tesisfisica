import numpy as np
import matplotlib.pyplot as plt

data = np.genfromtxt('C:/tesis git/tesisfisica/IVs/2211/A/3 terminales/tek0009ALL.csv', unpack=True, delimiter=',', skip_header=20)

plt.figure()
plt.plot(data[0],data[1])
plt.plot(data[0],data[2])
plt.plot(data[0],data[3])

data = np.genfromtxt('C:/tesis git/tesisfisica/IVs/2211/A/3 terminales/tek0010ALL.csv', unpack=True, delimiter=',', skip_header=20)

plt.figure()
plt.plot(data[0],data[1])
plt.plot(data[0],data[2])
plt.plot(data[0],data[3])
plt.show()