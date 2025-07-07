#%%
import numpy as np
from scipy.optimize import curve_fit
import os
import matplotlib.pyplot as plt
from natsort import natsorted
import csv
%matplotlib inline
dire = 'E:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/'
os.chdir('E:/porno/tesis 3/tesisfisica/eis/')
def get_files_with_path(folder):
    print(folder)
    return natsorted([os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))])
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return natsorted([name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))])
files = (list_folders_in_folder('E:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/'))

def zr(w, R, C):
    return R/(1+(w*R*C)**2)
def zi(w, R, C):
    return -w*R**2*C/(1+(w*R*C)**2)
#%%
output_csv = '1611_ajuste_zdew.csv'
with open(output_csv, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['T', 'Rre', 'Cre', 'Rim', 'Cim'])
for i in files:
    print(i)
    T = i.split('_')[-3].split('.')[0]
    data = np.genfromtxt(f'{dire}/{i}/Offset_0.00_mV.txt', delimiter=',', skip_header=1)
    w = data[1:, 0]
    re = data[1:, 1]
    im = data[1:, 3]
    poptre, pcovre = curve_fit(zr, w, re, p0=[1e3, 1e-9])
    fig, ax = plt.subplots(2,1,sharex=True)
    plt.suptitle(f'T = {T} K')
    ax[0].plot(w, re, 'b.', label='Experimental')
    ax[0].plot(w, zr(w, *poptre), 'r-', label='Ajuste')
    ax[0].set_xscale('log')
    ax[0].set_ylabel('Re(Z)')
    ax[0].legend()
    ax[0].grid()
    try:
        poptim, pcovim = curve_fit(zi, w, im, p0=[2,0])
    except:
        print('Falló')
        continue
    ax[1].plot(w, im, 'b.', label='Experimental')
    ax[1].plot(w, zi(w, *poptim), 'r-', label='Ajuste')
    ax[1].set_xscale('log')
    ax[1].set_ylabel('Im(Z)')
    ax[1].set_xlabel('Frecuencia (Hz)')
    ax[1].legend()
    ax[1].grid()
    plt.show()
    print(f'real: {poptre}')
    print(f'imaginary: {poptim}')
    with open(output_csv, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([T, poptre[0], poptre[1], poptim[0], poptim[1]])
    # break
#%%
fig, ax = plt.subplots(1,1,figsize=(9,7), dpi=800)
ax2 = ax.twinx()
data = np.genfromtxt('E:/porno/tesis 3/tesisfisica/IVs/1611_ajuste_zdew.csv', unpack=True, delimiter=',', skip_header=1)
ln1 = ax.scatter((1/data[0]), np.log(data[1]), color="#9858db", label='$R_{real}$')
ln2 = ax2.scatter((1/data[0]), np.log(data[2]), color="#c7c750", label='$C_{real}$')
ln3 = ax.scatter((1/data[0]), np.log(data[3]), color="#609ee0", label='$R_{img}$')
ln4 = ax2.scatter((1/data[0]), np.log(data[4]), color="#a1e067", label='$C_{img}$')
ax.set_xlabel('1/T (1/K)')
ax.set_ylabel('Log(R)')
ax2.set_ylabel('Log(C)')
ax.grid()
lines = [ln1, ln2, ln3, ln4]
labels = [line.get_label() for line in lines]
ax.legend(lines, labels)
# ax2.legend()
#%%
for i in files:
    print(i)
    T = i.split('_')[-3].split('.')[0]
    data = np.genfromtxt(f'{dire}/{i}/Offset_0.00_mV.txt', delimiter=',', skip_header=1)
    # if int(T) > 140:
    #     continue
    w = data[1:, 0]
    re = data[1:, 1]
    im = data[1:, 3]
    poptim, pcovim = curve_fit(zr, w, im, p0=[1e3, 1e-9])
    plt.scatter(re, -im, s=4, label=f'T = {T}K')
    plt.plot(zr(w, *poptim), -zi(w, *poptim), 'r-')
plt.xlabel('Re(Z)')
plt.ylabel('-Im(Z)')
# plt.ylim(-1e-3, 5)
# plt.xlim(-1, 4)
plt.grid()
plt.legend()
plt.show()
#%%
from impedance import preprocessing
from impedance.models.circuits import CustomCircuit
import csv
with open('Parametros_ajustados.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['T', 'R1', 'C1', 'L1', 'R2', 'C2', 'R3', 'C3'])
t = ['290', '270', '250', '230', '210', '190', '170', '150', '130', '110', '90', '70',
    '50', '30', '11']
initial_guess = [16.1,79.3e-6,0.855,3.48,24.9e-9,-20,67.9e-9]
for i in t:
    data = np.genfromtxt(f'E:/porno/tesis 3/tesisfisica/eis/0mvx5b/{i}k0.00mV_eis', unpack=True, delimiter='', skip_header=1)
    f = data[2][1:]
    Z = data[0][1:] - 1j*data[1][1:]

    circuit = 'p(R1-C1-L1,R2,C2)-p(R3,C3)'
    circuit = CustomCircuit(circuit, initial_guess=initial_guess)
    circuit.fit(f, Z, 
                bounds=([0, 0, 0, 0, 0, -3000, 0],
                        [np.inf, 1, np.inf, np.inf, 10, 0, 10]))

    paramteres = circuit.parameters_
    initial_guess = circuit.parameters_
    with open('Parametros_ajustados.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([i] + list(paramteres))
    print(f'T = {i}K')
    circuit.plot(f_data=f, Z_data=Z, kind='nyquist')
    circuit.plot(f_data=f, Z_data=Z, kind='bode')
    plt.show()
    print(circuit)
#%%
from impedance import preprocessing
from impedance.models.circuits import CustomCircuit
import csv
%matplotlib inline
with open('Parametros_ajustados_b.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['T', 'L1', 'R1', 'R2', 'C2', 'R3', 'C3'])
t = ['290', '270', '250', '230', '210', '190', '170', '150', '130', '110', '90']
initial_guess = [16, 4,1,24.9e-9,-1.3,1e-4]
for i in t:
    data = np.genfromtxt(f'E:/porno/tesis 3/tesisfisica/eis/0mvx5b/{i}k0.00mV_eis', unpack=True, delimiter='', skip_header=1)
    f = data[2][1:]
    Z = data[0][1:] - 1j*data[1][1:]

    circuit = 'p(L1-R1,R2,C2)-p(R3,C3)'
    circuit = CustomCircuit(circuit, initial_guess=initial_guess)
    circuit.fit(f, Z, 
                bounds=([0, 0, 0, 0, -300, 0],
                        [np.inf, np.inf, np.inf, 10, 0, 1]))

    paramteres = circuit.parameters_
    initial_guess = circuit.parameters_
    with open('Parametros_ajustados_b.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([i] + list(paramteres))
    print(f'T = {i}K')
    circuit.plot(f_data=f, Z_data=Z, kind='nyquist')
    circuit.plot(f_data=f, Z_data=Z, kind='bode')
    plt.show()
    print(circuit)
data = np.genfromtxt('E:/porno/tesis 3/tesisfisica/IVs/Parametros_ajustados_b.csv', unpack=True, delimiter=',', skip_header=1)
#%%
data = np.genfromtxt('E:/porno/tesis 3/tesisfisica/IVs/Parametros_ajustados_b.csv', unpack=True, delimiter=',', skip_header=1)
T, Lr, Rr, Rl, Cl, Rn, Cn = data
fig, ax= plt.subplots(3,1,figsize=(8, 7), sharex=True, dpi=800)
ax[1].set_ylabel('Capacitancia (F)')
ax[2].plot(1/T, Lr, 's-', label='Lr', c='#609ee0')      # Lr
ax[0].plot(1/T, Rr, 'o-', label='Rr', c='#e07b67')      # Rl
ax[0].plot(1/T, Rl, 'o-', label='Rl', c="#67e08f")      # Rl
# ax[1].plot(1/T, Cr, 'x-', label='Cl', c='#a1e067')     # Cl
ax[1].plot(1/T, Cl, 'x-', label='Cl', c='#a1e067')     # Cl
ax[1].plot(1/T, Cn, 'x-', label='Cn', c="#6f67e0")      # Rn
ax[0].plot(1/T, Rn, 'o-', label='Rn', c='#e067b7')      # Rn
ax[0].legend()
ax[1].legend()
ax[2].legend()
ax[0].grid()
# ax.set_yscale('log')
ax[1].set_yscale('log')
# Set log scale ticks for both y-axes
ax[1].grid()
ax[2].grid()
ax[2].set_xlabel('1/T (1/K)')
ax[0].set_ylabel('Resisencia ($\Omega$)')
ax[2].set_ylabel('Inductancia (H)')
#%% CON EL CIRCUITO NUEVO
from impedance import preprocessing
from impedance.models.circuits import CustomCircuit
import csv
%matplotlib inline
with open('Parametros_ajustados_cx5b.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['T', 'R1', 'L1', 'C1', 'R2', 'C2', 'R3', 'C3'])
t = ['290', '270', '250', '230', '210', '190', '170', '150', '130', '110', '90', '70']
initial_guess = [25, 13, 5.69e-10, -23, 10e-15, 6e-3 , 8.91e-4]
for i in t:
    data = np.genfromtxt(f'E:/porno/tesis 3/tesisfisica/eis/0mvx5b/{i}k0.00mV_eis', unpack=True, delimiter='', skip_header=1)
    f = data[2][1:-1]
    Z = data[0][1:-1] - 1j*data[1][1:-1]
    if i == '110':
        initial_guess = [250, 46.7, 1.11e-8, -250, 10e-15, 93 , 7.5]
    elif i == '90':
        initial_guess = [256, 46.7, 1.11e-8, -254, 10e-15, 93 , 7.5]
    elif i == '70':
        f = data[2][1:-3]
        Z = data[0][1:-3] - 1j*data[1][1:-3]
        initial_guess = [500, 200, 1.14e-28, -500, 5e-13, 93 , 12]
    # elif i == '50':
    #     f = data[2][1:-3]
    #     Z = data[0][1:-3] - 1j*data[1][1:-3]
    #     initial_guess = [162, 200, 2.2e-08, -155, 1.16e-8, 93 , 9]
    # else:
    #     continue
    circuit = 'p(R1,L1,C1)-p(R2,C2)-p(R3,C3)'
    circuit = CustomCircuit(circuit, initial_guess=initial_guess)
    circuit.fit(f, Z, 
                bounds=([0, 0, 0, -1000, 1e-15, 0, 0],
                        [np.inf, np.inf, 10, 0, 10, np.inf, 20]))

    paramteres = circuit.parameters_+'@'+circuit.conf_
    initial_guess = circuit.parameters_
    with open('Parametros_ajustados_cx5b.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([i] + list(paramteres))
    print(f'T = {i}K')
    circuit.plot(f_data=f, Z_data=Z, kind='nyquist')
    circuit.plot(f_data=f, Z_data=Z, kind='bode')
    plt.show()
    print(circuit)
#%%
data = np.genfromtxt('E:/porno/tesis 3/tesisfisica/eis/Parametros_ajustados_cx5b.csv', unpack=True, delimiter=',', skip_header=1)
T, Rl, Ll, Cl, Rn, Cn, Ra, Ca = data
fig, ax= plt.subplots(3,1,figsize=(8, 7), sharex=True, dpi=800)
ax[2].set_ylabel('Capacitancia (F)')
ax[0].plot(1/T, Rl, 'o-', label='Rl', c='#e07b67')      # Rl
ax[1].plot(1/T, Ll, 'o-', label='Ll', c='#609ee0')      # Ll
ax[2].plot(1/T, Cl, 'o-', label='Cl', c='#a1e067')     # Cl
ax[0].plot(1/T, Rn, 'o-', label='Rn', c="#67e08f")      # Rn
ax[2].plot(1/T, Cn, 'o-', label='Cn', c="#e0a767")     # Cn
ax[0].plot(1/T, Ra, 'o-', label='Ra', c="#6f67e0")      # Ra
ax[2].plot(1/T, Ca, 'o-', label='Ca', c='#e067b7')      # Ca
ax[0].legend()
ax[1].legend()
ax[2].legend()
ax[0].grid()
# ax.set_yscale('log')
ax[2].set_yscale('log')
# Set log scale ticks for both y-axes
ax[2].grid()
ax[1].grid()
ax[2].set_xlabel('1/T (1/K)')
ax[0].set_ylabel('Resisencia ($\Omega$)')
ax[1].set_ylabel('Inductancia (H)')
# %%
