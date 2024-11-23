import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import numpy as np

V, I, Vb, Ib = np.loadtxt('C:/tesis git/tesisfisica/criostato/Archivos/iv/iv-x5-d.csv', delimiter=',', unpack=True)
Vn, In, Vbn, Ibn = np.loadtxt('C:/tesis git/tesisfisica/criostato/Archivos/iv/iv-x5-d-n.csv', delimiter=',', unpack=True)

from scipy.optimize import curve_fit
def r(V,R):
    return V/R

popt, pcov = curve_fit(r, V, I, p0=2)
poptn, pcovn = curve_fit(r,Vn, In, p0=2)
x = np.linspace(0.0015,0.018,100)
xn = np.linspace(-0.0015,-0.018,100)
plt.scatter(V,I)
plt.scatter(Vn, np.abs(In), color='blue')
plt.grid()
plt.plot(x, r(x, popt),color = 'orange')
#plt.yscale('log')
#plt.xscale('log')
plt.plot(xn, np.abs(r(xn, poptn)),color = 'red')
plt.title(f'+r = {popt} $\Omega$ -r = {poptn} $\Omega$')
plt.xlabel('Voltaje [V]')
plt.ylabel('|I| [A]')
plt.show()