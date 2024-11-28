#%%
import numpy as np
import matplotlib.pyplot as plt


# Create a 2x2 grid of subplots
fig = plt.figure()
data = np.genfromtxt('C:/tesis git/tesisfisica/IVs/2611/B/tek0041ALL.csv', unpack=True, delimiter=',', skip_header=20)
x = data[6]
y = data[7]
plt.plot(x, y, label='Off 400', color="blue")
data = np.genfromtxt('C:/tesis git/tesisfisica/IVs/2611/B/tek0042ALL.csv', unpack=True, delimiter=',', skip_header=20)
x = data[6]
y = data[7]
plt.plot(x, y, label='Off 300', color="red")
data = np.genfromtxt('C:/tesis git/tesisfisica/IVs/2611/B/tek0043ALL.csv', unpack=True, delimiter=',', skip_header=20)
x = data[6]
y = data[7]
plt.plot(x, y, label='Off 200', color="green")
data = np.genfromtxt('C:/tesis git/tesisfisica/IVs/2611/B/tek0044ALL.csv', unpack=True, delimiter=',', skip_header=20)
x = data[6]
y = data[7]
plt.plot(x, y, label='Off 100', color="purple")
data = np.genfromtxt('C:/tesis git/tesisfisica/IVs/2611/B/tek0045ALL.csv', unpack=True, delimiter=',', skip_header=20)
x = data[6]
y = data[7]
plt.plot(x, y, label='Off 0', color="orange")
data = np.genfromtxt('C:/tesis git/tesisfisica/IVs/2611/B/tek0046MTH.csv', unpack=True, delimiter=',', skip_header=20)
x = data[0]
y = data[1]
plt.plot(x, y, label='Excitacion 0dc', color="black")
data = np.genfromtxt('C:/tesis git/tesisfisica/IVs/2611/B/tek0047MTH.csv', unpack=True, delimiter=',', skip_header=20)
x = data[0]
y = data[1]
plt.plot(x, y, label='Excitacion 400dc', color="cyan")
plt.grid()
plt.legend()
# Adjust layout
plt.tight_layout()

# Show the plot
plt.show()

