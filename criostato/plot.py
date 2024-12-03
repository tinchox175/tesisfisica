import matplotlib.pyplot as plt
import numpy as np
%matplotlib qt
dir = 'C:/tesis git/tesisfisica/criostato/Archivos/X5/'
filename = 'X5-811-c.csv'

T, s, h, v1, i1, r1, v2, i2, r2 = np.loadtxt(dir+filename, usecols=(1,2,3,4,5,6,7,8,9), delimiter=',', unpack=True, skiprows=1)

plt.scatter(T[:671], r1[:671]*0.065*0.02/0.053, color='red')
plt.scatter(T[772:1600],(r1[772:1600])*0.065*0.02/0.053, color='blue')
plt.scatter(T[673:771], r1[673:771]*0.065*0.02/0.053, color='violet')
plt.xlabel('T (K)')
plt.ylabel('$\\rho$ ($\Omega$ cm)')
#plt.ylim(1.5,3)
plt.grid()
plt.show()