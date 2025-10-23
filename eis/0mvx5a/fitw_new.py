#%%
import numpy as np
from scipy.optimize import curve_fit
import os
import matplotlib.pyplot as plt
from natsort import natsorted
import csv
%matplotlib inline
dire = 'e:/porno/tesis 3/tesisfisica/IVs/1812/ZdeW_1234_18-12-24/'
os.chdir('e:/porno/tesis 3/tesisfisica/eis/')
def get_files_with_path(folder):
    print(folder)
    return natsorted([os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))])
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return natsorted([name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))])
files = (list_folders_in_folder('e:/porno/tesis 3/tesisfisica/IVs/1812/ZdeW_1234_18-12-24/'))

def z(w, R1, L1, C1, R2, C2, R3, C3):
    w = 2*np.pi*w
    return 1/(1/R1+1/(1j*w*L1)+1j*w*C1)+1/(1/R2+1j*w*C2)+1/(1/R3+1j*w*C3)

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
data = np.genfromtxt('e:/porno/tesis 3/tesisfisica/IVs/1611_ajuste_zdew.csv', unpack=True, delimiter=',', skip_header=1)
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
fig, ax= plt.subplots(1,1,figsize=(4, 4), sharex=True, dpi=800)
for i in files:
    i = files[0]
    print(i)
    # T = i.split('_')[-3].split('.')[0]
    data = np.genfromtxt(f'{dire}/{i}/Offset_0.00_mV.txt', delimiter=',', skip_header=1)
    w = data[1:, 0]
    re = data[1:, 1]
    im = data[1:, 3]
    color = '#4c86f0'
    # Use the same color for scatter and plot for each curve
    sc = ax.scatter(re, -im, s=60, color=color)
    ax.plot(re, -im, '-', color=color, alpha=0.7)
    # z_vals = z(w, *(param[n] for param in params_tuple))
    # ax[0].plot(z_vals.real, -z_vals.imag, color=color, alpha=0.7, zorder=3)
plt.xlabel('Re(Z)')
plt.ylabel('-Im(Z)')
# plt.ylim(-1e-3, 5)
# plt.xlim(-1, 4)
plt.grid()
# plt.legend()
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
    data = np.genfromtxt(f'e:/porno/tesis 3/tesisfisica/eis/0mvx5b/{i}k0.00mV_eis', unpack=True, delimiter='', skip_header=1)
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
    data = np.genfromtxt(f'e:/porno/tesis 3/tesisfisica/eis/0mvx5b/{i}k0.00mV_eis', unpack=True, delimiter='', skip_header=1)
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
data = np.genfromtxt('e:/porno/tesis 3/tesisfisica/IVs/Parametros_ajustados_b.csv', unpack=True, delimiter=',', skip_header=1)
#%%
data = np.genfromtxt('e:/porno/tesis 3/tesisfisica/IVs/Parametros_ajustados_b.csv', unpack=True, delimiter=',', skip_header=1)
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
with open('Parametros_ajustados_cx5a.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['T', 'R1', 'L1', 'C1', 'R2', 'C2', 'R3', 'C3'])
t = ['280', '260', '240', '220', '200', '180', '160', '140', '120', '100', '85',]
initial_guess = [3.65, 0.46, 22e-9, -1.47, 47e-8, 3 , 1e-3]
for i in t:
    data = np.genfromtxt(f'e:/porno/tesis 3/tesisfisica/eis/0mvx5a/{i}k0.00mV_eis', unpack=True, delimiter='', skip_header=1)
    f = data[2][1:-1]
    Z = data[0][1:-1] - 1j*data[1][1:-1]
    circuit = 'p(R1,L1,C1)-p(R2,C2)-p(R3,C3)'
    # if i == '240':
    #     initial_guess = [5.59,0,1.28e-8,-3.09,1.33e-8,2.01e-2,7.78e-2]
    circuit = CustomCircuit(circuit, initial_guess=initial_guess)
    circuit.fit(f, Z, 
                bounds=([0, 0, 0, -1000, 1e-15, 0, 0],
                        [1000, 100, 10, 0, 10, np.inf, 20]))

    paramteres = [f"{p}@{c}" for p, c in zip(circuit.parameters_, circuit.conf_)]
    initial_guess = circuit.parameters_
    with open('Parametros_ajustados_cx5a.csv', mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([str(i)] + list(paramteres))
    print(f'T = {i}K')
    circuit.plot(f_data=f, Z_data=Z, kind='nyquist')
    circuit.plot(f_data=f, Z_data=Z, kind='bode')
    plt.show()
    print(circuit)
    # if i=='240':

    #     break
    # break
#%%
from matplotlib import cm
from matplotlib.colors import ListedColormap
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.legend import Legend
import matplotlib
matplotlib.rcParams.update({'font.size': 13})
data = np.genfromtxt('e:/porno/tesis 3/tesisfisica/eis/Parametros_ajustados_cx5a.csv', dtype=str, unpack=True, delimiter=',', skip_header=1)
T, Rl, Ll, Cl, Rn, Cn, Ra, Ca = data
# Separate magnitude and error for each parameter
def split_mag_err(arr):
    mag = []
    err = []
    for val in arr:
        if isinstance(val, bytes):
            val = val.decode()
        if '@' in val:
            m, e = val.split('@')
            mag.append(float(m))
            err.append(float(e))
        else:
            mag.append(float(val))
            err.append(np.nan)
    return np.array(mag), np.array(err)
T = T.astype(float)
Rl, Rl_err = split_mag_err(Rl)
Ll, Ll_err = split_mag_err(Ll)
Cl, Cl_err = split_mag_err(Cl)
Rn, Rn_err = split_mag_err(Rn)
Cn, Cn_err = split_mag_err(Cn)
Ra, Ra_err = split_mag_err(Ra)
Ca, Ca_err = split_mag_err(Ca)
# Create an array where each index contains all previous parameters as a tuple
all_params = []
for i in range(len(T)):
    params_tuple = (
        Rl[:i+1], Ll[:i+1], Cl[:i+1],
        Rn[:i+1], Cn[:i+1], Ra[:i+1], Ca[:i+1]
    )
    all_params.append(params_tuple)
fig, ax= plt.subplots(3,1,figsize=(7, 9), sharex=False, dpi=300)
ax[2].set_ylabel('Capacitancia (F)')
ax[0].errorbar(1/T, Rl, yerr=Rl_err, fmt='o-', label='$R_L$', c='#e07b67', capsize=3, elinewidth=1)      # Rl
ax[1].errorbar(T, Ll, yerr=Ll_err, fmt='o-', label='$L$', c='#e07b67', capsize=3, elinewidth=1)      # Ll
ax[2].errorbar(T, Cl, yerr=Cl_err, fmt='o-', label='$C_L$', c='#e07b67', capsize=3, elinewidth=1)     # Cl
ax[0].errorbar(1/T, abs(Rn), yerr=Rn_err, fmt='o-', label='$R_{neg}$', c="#67e08f", capsize=3, elinewidth=1)      # Rn
ax[2].errorbar(T, Cn, yerr=Cn_err, fmt='o-', label='$C_{neg}$', c="#67e08f", capsize=3, elinewidth=1)     # Cn
ax[0].errorbar(1/T, Ra, yerr=Ra_err, fmt='o-', label='$R_{est}$', c="#6f67e0", capsize=3, elinewidth=1)      # Ra
ax[2].errorbar(T, Ca, yerr=Ca_err, fmt='o-', label='$C_{est}$', c="#6f67e0", capsize=3, elinewidth=1)      # Ca
ax[0].legend( loc='lower right')
ax[1].legend()
ax[2].legend( loc='lower left')
ax[0].set_yscale('log')
ax[0].grid()
ax[1].invert_xaxis()
ax[2].invert_xaxis()
# ax.set_yscale('log')
ax[2].set_yscale('log')
# Set log scale ticks for both y-axes
ax[2].grid()
ax[1].grid()
ax[0].set_xlabel('1/T (1/K)')
ax[1].set_xlabel(' ')
ax[2].set_xlabel('T (K)')
ax[0].set_ylabel('Resistencia ($\Omega$)')
ax[1].set_ylabel('Inductancia (H)')
plt.tight_layout()
# Use a pastel colormap with distinct colors
pastel_colors = [
    "#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3", "#a6d854",
    "#ffd92f", "#e5c494", "#b3b3b3", "#b15928", "#1f78b4",
    "#fdbf6f", "#cab2d6", "#6a3d9a", "#ffff99", "#b2df8a"
]
fig, ax = plt.subplots(3,1, figsize=(7,9), dpi=300)
handles = []
labels = []
for n, i in enumerate(files[::-1]):
    T = i.split('_')[-3].split('.')[0]
    data = np.genfromtxt(f'{dire}/{i}/Offset_0.00_mV.txt', delimiter=',', skip_header=1)
    w = data[1:, 0]
    re = data[1:, 1]
    im = data[1:, 3]
    color = pastel_colors[n]
    # Use the same color for scatter and plot for each curve
    sc = ax[0].scatter(re, -im, s=14, label=f'T = {T}K', color=color)
    z_vals = z(w, *(param[n] for param in params_tuple))
    ax[0].plot(z_vals.real, -z_vals.imag, color=color, alpha=0.7, zorder=3)
    ax[1].scatter(w, np.sqrt(re**2+im**2), s=14, color=color)
    ax[1].plot(w, np.sqrt(z_vals.real**2+z_vals.imag**2), color=color, alpha=0.7, zorder=3)
    # Use arctan2 for correct phase wrapping
    ax[2].scatter(w, np.arctan2(im, re), color=color, s=14)
    ax[2].plot(w, np.arctan2(z_vals.imag, z_vals.real), color=color, alpha=0.7, zorder=3)
    handles.append(sc)
    labels.append(f'T = {T}K')

ax[0].set_xlabel('Re(Z)')
ax[0].set_ylabel('-Im(Z)')
ax[0].set_xlim(1.8,4)
ax[0].set_ylim(-1,9)
ax[1].set_xlabel(' ')
ax[1].set_ylabel('|Z| ($\Omega$)')
ax[1].set_xscale('log')
ax[1].set_yscale('log')
ax[1].set_ylim(1.7e0,2.8e1)
ax[2].set_xlabel('Frecuencia (Hz)')
ax[2].set_ylabel('$\\theta$ (rad)')
ax[2].set_xscale('log')
ax[2].set_ylim(-2.1,0.5)
ax[0].grid()
ax[1].grid()
ax[2].grid()

plt.tight_layout()
# Adjust subplot parameters to make room for the legend without shrinking the plots

plt.subplots_adjust(right=0.80)

# Place legend directly to the right, vertically centered
fig.legend(
    handles, labels,
    loc='center left',
    bbox_to_anchor=(0.81, 0.4),
    fontsize='12',
    title='Temperatura',
    borderaxespad=0.
)
plt.show()
