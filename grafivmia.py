import numpy as np
import matplotlib.pyplot as plt


# Create a 2x2 grid of subplots
fig = plt.figure()
data = np.genfromtxt('C:/tesis git/tesisfisica/criostato/archivos/iv/iv-x5-d.csv', unpack=True, delimiter=',', skip_header=3)
x = data[0]
y = data[1]
plt.plot(x, y, label='Off 400', color="blue")
data = np.genfromtxt('C:/tesis git/tesisfisica/criostato/archivos/iv/iv-x5-d-n.csv', unpack=True, delimiter=',', skip_header=3)
x = data[0]
y = data[1]
plt.plot(x, y, label='Off 400', color="blue")
plt.show()