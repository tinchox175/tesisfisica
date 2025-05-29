import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

archivo = '' #Path del archivo

def z_real(w, R, C):
    return R/(1+(w*R*C)**2) #parte real de la impedancia

def z_imag(w, R, C):
    return -w*R**2*C/(1+(w*R*C)**2) #parte imaginaria de la impedancia

T = archivo.split('-')[-1] #Extrae la temperatura del nombre del archivo
data = np.genfromtxt(archivo, delimiter=',', skip_header=1) #Carga los datos del archivo
w = data[1:, 0] #Frecuencia en Hz
re = data[1:, 1] #Parte real de la impedancia
im = data[1:, 3] #Parte imaginaria de la impedancia
poptre, pcovre = curve_fit(z_real, w, re, p0=[1e3, 1e-9]) #Ajuste de la parte real de la impedancia
fig, ax = plt.subplots(2,1,sharex=True) #Crea una figura con dos subgráficas
plt.suptitle(f'T = {T} K')
ax[0].plot(w, re, 'b.', label='Experimental') #Grafica la parte real experimental
ax[0].plot(w, z_real(w, *poptre), 'r-', label='Ajuste') #Grafica la parte real ajustada
ax[0].set_xscale('log')
ax[0].set_ylabel('Re(Z)')
ax[0].legend()
ax[0].grid()
poptim, pcovim = curve_fit(z_imag, w, im, p0=[2,0]) #Ajuste de la parte imaginaria de la impedancia
ax[1].plot(w, im, 'b.', label='Experimental') #Grafica la parte imaginaria experimental
ax[1].plot(w, z_imag(w, *poptim), 'r-', label='Ajuste') #Grafica la parte imaginaria experimental y ajustada
ax[1].set_xscale('log')
ax[1].set_ylabel('Im(Z)')
ax[1].set_xlabel('Frecuencia (Hz)')
ax[1].legend()
ax[1].grid()
plt.show()
print(f'Parámetros derivados del ajuste parte real: {poptre}') 
print(f'Parámetros derivados del ajuste parte imaginaria: {poptim}')

plt.figure(figsize=(6, 4))
data = np.genfromtxt(archivo, delimiter=',', skip_header=1)
poptim, pcovim = curve_fit(z_real, w, im, p0=[1e3, 1e-9]) #Ajuste de la parte real/imaginaria de la impedancia
plt.scatter(re, -im, s=4, label=f'T = {T}K') #Grafica el Nyquist
plt.plot(z_real(w, *poptim), -z_imag(w, *poptim), 'r-') #Grafica el ajuste en el Nyquist
plt.xlabel('Re(Z)')                                     #con los parámetros seleccionados
plt.ylabel('-Im(Z)')
plt.grid()
plt.legend()
plt.show()
