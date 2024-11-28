import numpy as np
import matplotlib.pyplot as plt
import os
import itertools
from matplotlib.colors import Normalize

def get_files_with_path(folder):
    print(folder)
    return [os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]
%matplotlib qt
X = []
Y = []
Z = []
dirs = "C:/tesis git/tesisfisica/IVs/2211/ZdeW_1213_20-11-24/"
fil = list_folders_in_folder(dirs)
for j in fil:
    folder_path = dirs+j
    if folder_path.split('.')[-1] == 'png' or folder_path.split('.')[-1] == 'txt':
        pass
    files = get_files_with_path(folder_path)

    fig = plt.figure(f'{folder_path.split('_')[5]} K')
    ax = fig.add_subplot(111, projection='3d')
    fig.suptitle(f'{folder_path.split('_')[5]} K')
    fig.subplots_adjust(top=1.1, bottom=-.1)
    Zfalse = []
    for i in files:
        data = np.genfromtxt(i, unpack=True, delimiter=',')
        Zfalse.append(data[1][2:])
    for i in files:
        data = np.genfromtxt(i, unpack=True, delimiter=',')
        X = data[0][2:]
        Z = data[1][2:]
        Y = np.full_like(X, (i.split('_')[-2]).split('.')[0])
        norm = Normalize(vmin=np.min(Zfalse), vmax=np.max(Zfalse))
        sc = ax.scatter(np.log10(X), Y, Z, edgecolors= "black", c=Z, cmap='viridis', norm=norm, s=500)
        ax.set_xlabel('Log10(f) [Hz]')
        ax.set_ylabel('Offset [mV]')
        ax.set_zlabel('Resistencia [Ohm]')
    cbar = fig.colorbar(sc, ax=ax, label='Resistencia [Ohm]')
plt.show()