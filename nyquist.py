import numpy as np
import matplotlib.pyplot as plt
import os
import itertools
from matplotlib.colors import Normalize
import matplotlib.colors as colorz
import matplotlib.ticker as mticker
def get_files_with_path(folder):
    print(folder)
    return [os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]
def log_tick_formatter(val, pos=None):
    return f"$10^{{{int(val)}}}$"
from matplotlib.colors import LinearSegmentedColormap
from scipy.interpolate import griddata

n = 0
dirs = "D:/porno/tesis 3/tesisfisica/IVs/2711/ZdeW_1234_28-11-24-50mV/"
X = []
Y = []
deris = list_folders_in_folder(dirs)
for j in deris:
    files = get_files_with_path(dirs+j)
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(5, 7))
    fig.suptitle(f'{j.split('_')[-3]} K')
    fig.subplots_adjust(top=1.1, bottom=-.1)
    for i in files:
        print(i)
        if 'eis' in i:
            continue
        data = np.genfromtxt(i, unpack=True, delimiter=',')
        X = data[1]
        Y = data[3]
        Z = np.sqrt(X**2 + Y**2)
        theta = np.arctan(X/R)
        ax1.scatter(X, -Y, label=f'{i.split("_")[-2]} mV')
    locmaj = mticker.LogLocator(base=10,numticks=12) 
    ax1.xaxis.set_major_locator(locmaj)    
    locmin = mticker.LogLocator(base=10.0,subs=(0.2,0.4,0.6,0.8),numticks=12)
    ax1.xaxis.set_minor_locator(locmin)
    ax1.xaxis.set_minor_formatter(mticker.NullFormatter())
    ax1.set_xlabel(r'Z´ [$\Omega$]')
    ax1.set_ylabel(r'-Z´´ [$\Omega$]')
    ax1.set_yscale('symlog',linthresh=0.0001)
    ax1.set_xscale('symlog')
    ax1.legend()
    ax1.grid(True) 
    plt.tight_layout()
    os.chdir(dirs)
    plt.savefig(f'{j.split("_")[-3]}K.png', dpi=300)