#%% Analisis de pares de rampas

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from matplotlib.colorbar import ColorbarBase
import os
from natsort import natsorted
import itertools
%matplotlib ipympl
marker_l = lambda : itertools.cycle(('.',
 'o',
 'v',
 '^',
 '<',
 '>',
 '1',
 '2',
 '3',
 '4',
 '8',
 's',
 'p',
 '*',
 'h',
 'H',
 '+',
 'x',
 'D',
 'd',
 '|',
 'P',
 'X',
 0,
 1,
 2,
 3,
 4,
 5,
 6,
 7,
 8,
 9,
 10,
 11,
))

def get_files_with_path(folder):
    print(folder)
    return [os.path.join(folder, file) for file in sorted(os.listdir(folder)) if os.path.isfile(os.path.join(folder, file))]
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]

colors = [
    '#0CA0DC',  # Muted Cornflower Blue
    '#2A9D8F',  # Teal Green,  # Soft Lilac / Light Purple
    '#90BE6D',  # Pastel / Apple Green
    '#F9C74F',   # Saffron / Soft Yellow-Gold
    '#E63946',  # Vibrant Red/Pink (not primary red)
    '#C77DFF',
    'k'
]

# Create a colormap
dirs2 = get_files_with_path('e:/porno/tesis 3/tesisfisica/IVs/rampasT-ZdeW/temp')
dirs = []
for i in dirs2:
    if 'txt' in i:
        dirs.append(i)
dirs = sorted(
    dirs,
    key=lambda path: int(os.path.basename(path).removesuffix('.txt').split('Temp')[-1])
)
fig, axs = plt.subplots(2, 2, figsize=(12, 9), sharex=True)
s=10
n = 0
bounds = []
for i in dirs:
    print(i)
    data = np.genfromtxt(i, unpack=True, delimiter=',')
    time = data[0][2:]
    T = data[2][2:]
    Z40 = data[5][2:]
    t40 = data[6][2:]
    Z200k = data[7][2:]
    t200k = data[8][2:]
    R40 = Z40*np.cos(t40*np.pi/180)
    X40 = t40*np.sin(t40*np.pi/180)
    R200k = Z200k*np.cos(t200k*np.pi/180)
    X200k = t200k*np.sin(t200k*np.pi/180)
    vac, vdc = data[-6][10], data[-5][10]
    if int(vdc)==75:
        sc1 = axs[0, 0].plot(T[:50], X40[:50], color=colors[n], label=f'{i.split("_")[2].split('-')[0]}.{i.split("_")[2].split('-')[1]}' + ' $V_{ac}$='+str(vac)+' mV $V_{dc}$=' +str(vdc)+ ' mV') 
        sc2 = axs[0, 1].plot(T[:50], X200k[:50], color=colors[n])
        sc3 = axs[1, 0].plot(T[:50], R40[:50], color=colors[n])
        sc4 = axs[1, 1].plot(T[:50], R200k[:50], color=colors[n])
        sc1 = axs[0, 0].plot(T[50:120], X40[50:120], color=colors[n]) 
        sc2 = axs[0, 1].plot(T[50:120], X200k[50:120], linestyle='dashed', color=colors[n])
        sc3 = axs[1, 0].plot(T[50:120], R40[50:120], linestyle='dashed', color=colors[n])
        sc4 = axs[1, 1].plot(T[50:120], R200k[50:120], linestyle='dashed', color=colors[n])
        sc1 = axs[0, 0].plot(T[120:], X40[120:], color=colors[n]) 
        sc2 = axs[0, 1].plot(T[120:], X200k[120:], color=colors[n])
        sc3 = axs[1, 0].plot(T[120:], R40[120:], color=colors[n])
        sc4 = axs[1, 1].plot(T[120:], R200k[120:], color=colors[n])
        n+=1
    else:
        sc1 = axs[0, 0].plot(T, X40, color=colors[n], label=f'{i.split("_")[2].split('-')[0]}.{i.split("_")[2].split('-')[1]}' + ' $V_{ac}$='+str(vac)+' mV $V_{dc}$=' +str(vdc)+ ' mV') 
        sc2 = axs[0, 1].plot(T, X200k, color=colors[n])
        sc3 = axs[1, 0].plot(T, R40, color=colors[n])
        sc4 = axs[1, 1].plot(T, R200k, color=colors[n])
        n+=1
# axs[1,0].scatter(290, 2.5, marker='x', s=50, c='#E63946')
# axs[1,0].scatter(290, 1.12, marker='x', s=50, c='#2A9D8F')
# axs[1,0].scatter(290, 0.8, marker='x', s=50, c='#F9C74F')
# axs[1,0].scatter(290, 0.66, marker='x', s=50, c='#C77DFF')
# axs[1,0].scatter(290, 0.53, marker='x', s=50, c='k')
# axs[1,0].scatter(200, 3.5, marker='x', s=50, c='#E63946')
# axs[1,0].scatter(200, 1.6, marker='x', s=50, c='#2A9D8F')
# axs[1,0].scatter(200, 1.2, marker='x', s=50, c='#F9C74F')
# axs[1,0].scatter(200, 1.0, marker='x', s=50, c='#C77DFF')
# axs[1,0].scatter(200, 0.8, marker='x', s=50, c='k')
# axs[1,1].scatter(290, 2.3, marker='x', s=50, c='#E63946')
# axs[1,1].scatter(290, 1.12, marker='x', s=50, c='#2A9D8F')
# axs[1,1].scatter(290, 0.8, marker='x', s=50, c='#F9C74F')
# axs[1,1].scatter(290, 0.66, marker='x', s=50, c='#C77DFF')
# axs[1,1].scatter(290, 0.53, marker='x', s=50, c='k')
# axs[1,1].scatter(200, 3.5, marker='x', s=50, c='#E63946')
# axs[1,1].scatter(200, 1.6, marker='x', s=50, c='#2A9D8F')
# axs[1,1].scatter(200, 1.2, marker='x', s=50, c='#F9C74F')
# axs[1,1].scatter(200, 1.0, marker='x', s=50, c='#C77DFF')
# axs[1,1].scatter(200, 0.8, marker='x', s=50, c='k')
axs[0,0].set_ylabel('X ($\Omega$)')
axs[1,1].set_xlabel('T (K)')
axs[1,0].set_xlabel('T (K)')
axs[1,0].set_ylabel('R ($\Omega$)')
axs[0,0].grid(True)
axs[1,0].grid(True)
axs[0,1].grid(True)
axs[1,1].grid(True)
# axs[0,0].set_ylim(0,150)
# axs[1,0].set_ylim(0,10)
# axs[1,1].set_ylim(-12,5)
# axs[0,1].set_ylim(0,130)
# axs[0,0].set_yscale('symlog', linthresh=1e-1)
# axs[0,1].set_yscale('symlog', linthresh=1e1)
# axs[1,0].set_yscale('symlog', linthresh=1e0)
# axs[1,1].set_yscale('symlog', linthresh=1e1)
axs[0,0].set_title('40 Hz')
axs[0,1].set_title('200 kHz')
# axs[0,0].legend()
num_categories = 7
category_values = np.arange(num_categories)
bounds = np.linspace(-0.5, num_categories - 0.5, num_categories + 1)
tick_locs = category_values 
cmap = mcolors.ListedColormap(colors)
norm = mcolors.BoundaryNorm(bounds, cmap.N)
cbar_ax_rect = [0.92, 0.11, 0.03, 0.77]
cbar_ax = fig.add_axes(cbar_ax_rect)
cbar = fig.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), cax=cbar_ax, ticks=tick_locs, orientation='vertical')
cbar.ax.set_yticklabels([100, 200, 300, 400])
cbar.set_label('Polarización DC (mV)')
plt.show()
# plt.tight_layout()
# plt.show()
plt.savefig('fig.png')
#%%
#%% Analisis de pares de rampas

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from matplotlib.colorbar import ColorbarBase
import os
from natsort import natsorted
import itertools
%matplotlib ipympl
marker_l = lambda : itertools.cycle(('.',
 'o',
 'v',
 '^',
 '<',
 '>',
 '1',
 '2',
 '3',
 '4',
 '8',
 's',
 'p',
 '*',
 'h',
 'H',
 '+',
 'x',
 'D',
 'd',
 '|',
 'P',
 'X',
 0,
 1,
 2,
 3,
 4,
 5,
 6,
 7,
 8,
 9,
 10,
 11,
))

def get_files_with_path(folder):
    print(folder)
    return [os.path.join(folder, file) for file in sorted(os.listdir(folder)) if os.path.isfile(os.path.join(folder, file))]
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]
colors = [
    '#FF0000',  # Red
    '#FFA500',  # Orange
    '#FFFF00',  # Yellow
    '#008000',  # Green
    '#0000FF',  # Blue
    '#8A2BE2'   # BlueViolet / Indigo
]
dirs2 = get_files_with_path('e:/porno/tesis 3/tesisfisica/IVs/rampasT-ZdeW/temp')
dirs = []
for i in dirs2:
    if 'txt' in i:
        dirs.append(i)
dirs = sorted(
    dirs,
    key=lambda path: int(os.path.basename(path).removesuffix('.txt').split('Temp')[-1])
)
fig, axs = plt.subplots(2, 2, figsize=(9.5, 7), sharex=True)
n=0
for i in dirs:
    data = np.genfromtxt(i, unpack=True, delimiter=',')
    time = data[0][1:]
    T = data[2][1:]
    norm = mcolors.Normalize(vmin=min(time), vmax=max(time))
    Z40 = data[5][1:]
    t40 = data[6][1:]
    R40 = Z40*np.cos(t40*np.pi/180)
    X40 = t40*np.sin(t40*np.pi/180)
    Z200k = data[7][1:]
    t200k = data[8][1:]
    R200k = Z200k*np.cos(t200k*np.pi/180)
    X200k = t200k*np.sin(t200k*np.pi/180)
    vac, vdc = data[-5][10], data[-4][10]
    if np.min(T)>50 and '_08-12-24b_' not in i:
        sc1 = axs[0, 0].plot(T[:], t40[:], color=colors[n],  label=f'{i.split("_")[1].split('-')[0]}.{i.split("_")[1].split('-')[1]}' + ' $V_{ac}$='+str(vac)+' mV $V_{dc}$=' +str(vdc)+ ' mV')
        sc2 = axs[0, 1].plot(T[:], t200k[:], color=colors[n])
        sc3 = axs[1, 0].plot(T[:], Z40[:], color=colors[n])
        sc4 = axs[1, 1].plot(T[:], Z200k[:], color=colors[n])
    else:
        sc1 = axs[0, 0].scatter(T[:], t40[:], s=7, color=colors[n],  label=f'{i.split("_")[1].split('-')[0]}.{i.split("_")[1].split('-')[1]}' + ' $V_{ac}$='+str(vac)+' mV $V_{dc}$=' +str(vdc)+ ' mV')
        sc2 = axs[0, 1].scatter(T[:], t200k[:], s=7, color=colors[n])
        sc3 = axs[1, 0].scatter(T[:], Z40[:], s=7, color=colors[n])
        sc4 = axs[1, 1].scatter(T[:], Z200k[:], s=7, color=colors[n])
    n+=1
axs[0,0].set_ylabel('$\Theta$')
axs[1,1].set_xlabel('T (K)')
axs[1,0].set_xlabel('T (K)')
axs[1,0].set_ylabel('Z ($\Omega$)')
axs[0,0].grid(True)
axs[1,0].grid(True)
axs[0,1].grid(True)
axs[1,1].grid(True)
axs[1,0].set_yscale('symlog')
axs[1,1].set_yscale('symlog')
axs[1,0].set_ylim(0,100)
cmap = mcolors.ListedColormap(colors)
bounds = np.arange(6)  # Discrete levels from 0 to 10
norm = mcolors.BoundaryNorm(bounds, cmap.N)
cbar_ax_rect = [0.92, 0.11, 0.03, 0.77]
cbar_ax = fig.add_axes(cbar_ax_rect)
cbar = fig.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), cax=cbar_ax, orientation='vertical', pad=0.02)
cbar.ax.set_yticklabels([str(i) for i in range(6)])
cbar.set_label('Offset (mV)')
# plt.savefig(f'E:/porno/tesis 3/tesisfisica/IVs/rampasT-ZdeW/RampaTenLCRZT.png')

