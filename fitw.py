#%%
import numpy as np
from scipy.optimize import curve_fit
import os
import matplotlib.pyplot as plt
from natsort import natsorted
import csv
%matplotlib inline
dire = 'C:/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/'
os.chdir('C:/tesisfisica/IVs/')
def get_files_with_path(folder):
    print(folder)
    return natsorted([os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))])
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return natsorted([name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))])
files = (list_folders_in_folder('C:/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/'))

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
    plt.suptitle(i)
    ax[0].plot(w, re, 'b.', label='data')
    ax[0].plot(w, zr(w, *poptre), 'r-', label='fit')
    ax[0].set_xscale('log')
    ax[0].legend()
    ax[0].grid()
    try:
        poptim, pcovim = curve_fit(zi, w, im, p0=[2,0])
    except:
        print('Falló')
        continue
    ax[1].plot(w, im, 'b.', label='data')
    ax[1].plot(w, zi(w, *poptim), 'r-', label='fit')
    ax[1].set_xscale('log')
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
fig, ax = plt.subplots(1,1,figsize=(9,7))
ax2 = ax.twinx()
data = np.genfromtxt('c:/tesisfisica/IVs/1611_ajuste_zdew.csv', unpack=True, delimiter=',', skip_header=1)
ln1 = ax.scatter(int(data[0]), int(data[1]), color='#ccb3e6', label='$R_{real}$')
ln2 = ax2.scatter(int(data[0]), int(data[2]), color='#cccc99', label='$C_{real}$')
ln3 = ax.scatter(int(data[0]), int(data[3]), color='#b3cce6', label='$R_{img}$')
ln4 = ax2.scatter(int(data[0]), int(data[4]), color='#cce6b3', label='$C_{img}$')
ax.grid()
plt.legend()
