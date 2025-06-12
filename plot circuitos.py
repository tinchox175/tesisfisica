#%%
import matplotlib.pyplot as plt
import numpy as np
%matplotlib inline
plt.rcParams.update({'font.size': 16})
def Z(w, L, Rr, R, C, Rn, Cn):
    w = w*(2 * np.pi)  # Convert frequency to Hz
    return 1/(1/Rn+1/(1/(1j*w*Cn))) + 1/(1/R + (1/(1j*w*L+Rr)) + 1/(1/(1j*w*C)))

data = np.genfromtxt('E:/porno/tesis 3/tesisfisica/IVs/Parametros_ajustados_b.csv', unpack=True, delimiter=',', skip_header=1)
T, Lr, Rr, Rl, Cl, Rn, Cn = data[:,7]
p = Lr, Rr, Rl, Cl, Rn, Cn
data2 = np.genfromtxt(f'E:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/ZdeW_1234_Temperatura_140.37_K_1719/Offset_20.00_mV.txt', delimiter=',', skip_header=1)
w = data2[1:, 0]
re = data2[1:, 1]
im = data2[1:, 3]


fig, ax = plt.subplots(2,1,figsize=(10, 6), sharex=True)
plt.suptitle(f'T = {int(T)} K')
ax[0].scatter(w, re, c='b', label='Datos')
ax[0].plot(w, Z(w, *p).real, 'r-', label='Ajuste')
ax[1].scatter(w, im, c='b',)
ax[1].plot(w, Z(w, *p).imag, 'r-')


# Add labels and title
ax[1].set_xlabel('Frecuencia (Hz)')
ax[0].set_ylabel('Re(Z) (Ohm)')
ax[1].set_ylabel('Im(Z) (Ohm)')
ax[0].set_xscale('log')
ax[0].grid(True)
ax[1].set_xscale('log')
ax[1].grid(True)
ax[0].legend()

#%%
import numpy as np
from scipy.optimize import curve_fit
import os
import matplotlib.pyplot as plt
from natsort import natsorted
import csv
plt.rcParams.update({'font.size': 10})
%matplotlib inline

def Z(w, L, Rr, R, C, Rn, Cn):
    w = w*(2 * np.pi)  # Convert frequency to Hz
    return 1/(1/Rn+1/(1/(1j*w*Cn))) + 1/(1/R + (1/(1j*w*L+Rr)) + 1/(1/(1j*w*C)))

dire = 'E:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/'
os.chdir('E:/porno/tesis 3/tesisfisica/IVs/')
def get_files_with_path(folder):
    print(folder)
    return natsorted([os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))])
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return natsorted([name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))])
files = (list_folders_in_folder('E:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/'))
n= len(files)-1
for i in files:
    print(i)
    data2 = np.genfromtxt('E:/porno/tesis 3/tesisfisica/IVs/Parametros_ajustados_b.csv', unpack=True, delimiter=',', skip_header=1)
    T, Lr, Rl, Cl, Rn, Cn = data2[:,n]
    p = Lr, Rl, Cl, Rn, Cn
    T = i.split('_')[-3].split('.')[0]
    data = np.genfromtxt(f'{dire}/{i}/Offset_20.00_mV.txt', delimiter=',', skip_header=1)
    w = data[1:, 0]
    re = data[1:, 1]
    im = data[1:, 3]
    plt.scatter(re, -im, s=4, label=f'T = {T}K')
    plt.plot(Z(w, *p).real, -Z(w, *p).imag, 'r-')
    plt.xlim(0,5)
    plt.ylim(-5,10)
    n-=1
plt.xlabel('Re(Z)')
plt.ylabel('-Im(Z)')
# plt.ylim(-1e-3, 5)
# plt.xlim(-1, 4)
plt.grid()
plt.legend()
plt.show()
#%%
data = np.genfromtxt('E:/porno/tesis 3/tesisfisica/IVs/Parametros_ajustados_b.csv', unpack=True, delimiter=',', skip_header=1)
T, Lr, Rl, Cl, Rn = data[:,-1]
p = Lr, Rl, Cl, Rn
data2 = np.genfromtxt(f'E:/porno/tesis 3/tesisfisica/IVs/1812\ZdeW_1234_18-12-24\ZdeW_1234_Temperatura_291.02_K_1051/Offset_0.00_mV.txt', delimiter=',', skip_header=1)
w = data2[1:, 0]
re = data2[1:, 1]
im = data2[1:, 3]


fig, ax = plt.subplots(2,1,figsize=(10, 6), sharex=True)
plt.suptitle(f'T = {int(T)} K')
ax[0].scatter(w, re, c='b', label='Datos')
ax[0].plot(w, Z(w, *p).real, 'r-', label='Ajuste')
ax[1].scatter(w, im, c='b',)
ax[1].plot(w, Z(w, *p).imag, 'r-')


# Add labels and title
ax[1].set_xlabel('Frecuencia (Hz)')
ax[0].set_ylabel('Re(Z) (Ohm)')
ax[1].set_ylabel('Im(Z) (Ohm)')
ax[0].set_xscale('log')
ax[0].grid(True)
ax[1].set_xscale('log')
ax[1].grid(True)
ax[0].legend()

#%%
import numpy as np
from scipy.optimize import curve_fit
import os
import matplotlib.pyplot as plt
from natsort import natsorted
import csv
plt.rcParams.update({'font.size': 10})
def Z(w, L, Rr, R, C, Rn, Cn):
    w = w*(2 * np.pi)  # Convert frequency to Hz
    return 1/(1/Rn+1/(1/(1j*w*Cn))) + 1/(1/R + (1/(1j*w*L+Rr)) + 1/(1/(1j*w*C)))
%matplotlib inline
dire = 'E:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/'
os.chdir('E:/porno/tesis 3/tesisfisica/IVs/')
def get_files_with_path(folder):
    print(folder)
    return natsorted([os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))])
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return natsorted([name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))])
files = (list_folders_in_folder('E:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/'))
n= len(files)-1
for i in files:
    print(i)
    data2 = np.genfromtxt('E:/porno/tesis 3/tesisfisica/IVs/Parametros_ajustados_b.csv', unpack=True, delimiter=',', skip_header=1)
    T, Lr, Rr, Rl, Cl, Rn, Cn = data2[:,n]
    p = Lr, Rr, Rl, Cl, Rn, Cn
    T = i.split('_')[-3].split('.')[0]
    data = np.genfromtxt(f'{dire}/{i}/Offset_20.00_mV.txt', delimiter=',', skip_header=1)
    w = data[1:, 0]
    re = data[1:, 1]
    im = data[1:, 3]
    plt.scatter(re, -im, s=4, label=f'T = {T}K')
    plt.plot(Z(w, *p).real, -Z(w, *p).imag, 'r-')
    n-=1
plt.xlabel('Re(Z)')
plt.ylabel('-Im(Z)')
plt.ylim(-1, 5)
plt.xlim(-1, 4)
plt.grid()
plt.legend()
plt.show()
#%%
import numpy as np
import os
import matplotlib.pyplot as plt
from natsort import natsorted
import csv
%matplotlib inline
dire = 'E:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/'
os.chdir('E:/porno/tesis 3/tesisfisica/IVs/')
def get_files_with_path(folder):
    print(folder)
    return natsorted([os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))])
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return natsorted([name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))])
files = (list_folders_in_folder('E:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/'))
for i in files:
    print(i)
    T = i.split('_')[-3].split('.')[0]
    data = np.genfromtxt(f'{dire}/{i}/Offset_20.00_mV.txt', delimiter=',', skip_header=1)
    w = data[1:, 0]
    re = data[1:, 1]
    im = data[1:, 3]
    output_path = os.path.join(os.path.dirname(dire), f"{T}k20.00mV_eis")
    np.savetxt(output_path, np.column_stack((re, -im, w)), delimiter=' ', header='re, im, w')