#%%
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
#%%
%matplotlib qt
X = []
Y = []
Z = []
dirs = "C:/tesis git/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
fil = list_folders_in_folder(dirs)
for j in fil:
    folder_path = dirs+j
    if folder_path.split('.')[-1] == 'png' or folder_path.split('.')[-1] == 'txt':
        pass
    files = get_files_with_path(folder_path)

    fig = plt.figure(f'{folder_path.split('_')[5]} K', figsize=(12,8))
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
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(log_tick_formatter))
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax.set_xlabel('f [Hz]')
        ax.set_ylabel('Offset [mV]')
        ax.set_zlabel('Resistencia [Ohm]')
    cbar = fig.colorbar(sc, ax=ax, label='Resistencia [Ohm]')
    plt.tight_layout()
plt.show()
#%%
from matplotlib.colors import LinearSegmentedColormap
from scipy.interpolate import griddata
colors = [
    (0.0, "#000000"),   # Black at -5
    (0.1, "#2c105c"),   # Deep purple
    (0.15, "#3d28a0"),  # Violet
    (0.2, "#4141a5"),   # Rich blue
    (0.25, "#0072ff"),  # Bright blue
    (0.3, "#00a5ff"),   # Sky blue
    (0.35, "#00d8ff"),  # Cyan
    (0.4, "#7dffba"),   # Aquamarine
    (0.45, "#a8ffc7"),  # Mint green
    (0.5, "#d4ffd3"),   # Soft green
    (0.55, "#ffff5e"),  # Bright yellow
    (0.6, "#ffd700"),   # Gold
    (0.7, "#ffa600"),   # Warm orange
    (0.8, "#ff3d00"),   # Deep orange-red
    (0.9, "#ff9cfb"),   # Light pink
    (1.0, "#ffffff")    # White at 10
]
X = []
Y = []
Z = []
X0 = []
Y0 = []
Z0 = []
dirs = "C:/tesis git/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
fil = list_folders_in_folder(dirs)
for j in fil:
    folder_path = dirs+j
    if folder_path.split('.')[-1] == 'png' or folder_path.split('.')[-1] == 'txt':
        pass
    files = get_files_with_path(folder_path)

    fig = plt.figure(f'{folder_path.split('_')[5]} K', figsize=(12,8))
    ax = fig.add_subplot(111)
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
        X0 = np.append(X0,X)
        Y0 = np.append(Y0,Y)
        Z0 = np.append(Z0,Z)
        norm = Normalize(vmin=-5, vmax=10)
        positions, color_names = zip(*colors)
        # sc = ax.scatter(X, Y, edgecolors= "black", c=Z, cmap = LinearSegmentedColormap.from_list("custom_cmap", list(colors)), norm=norm, s=500)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(log_tick_formatter))
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax.axvline(180,0,200, c='gray', ls='--')
        ax.axvline(29000, 0, 200, c='gray', ls='--')
        ax.set_xlabel('f [Hz]')
        ax.set_ylabel('Offset [mV]')
        ax.set_xscale('log')
        ax.grid(True) 
    #cbar = fig.colorbar(sc, ax=ax, label='Resistencia [Ohm]')
    xi = np.linspace(np.min(X0), np.max(X0), 1000)  # 200 is an example resolution
    yi = np.linspace(np.min(Y0), np.max(Y0), 1000)
    Xi, Yi = np.meshgrid(xi, yi)
    Zi = griddata((X0, Y0), Z0, (Xi, Yi), method='nearest')
    mesh = ax.pcolormesh(Xi, Yi, Zi, cmap='viridis', shading='auto')
    plt.colorbar(mesh, label='Resistance [Ohm]')
    plt.tight_layout()
    # plt.savefig(f'c:/tesis git/tesisfisica/figuras/{float(folder_path.split('_')[5])} fvr.png')
    break
plt.show()
# %%
