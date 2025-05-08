# -*- coding: utf-8 -*-
#%%
import numpy as np
import matplotlib.pyplot as plt
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
    return [os.path.join(folder, file) for file in natsorted(os.listdir(folder)) if os.path.isfile(os.path.join(folder, file))]
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]
#%%
dirs = "E:/porno/tesis 3/tesisfisica/IVs/1812/ZdeW_1234_18-12-24/"
# dirs = "E:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"

fil = list_folders_in_folder(dirs)
for j in fil:
    fig, (ax2, ax1) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    folder_path = dirs+j
    if folder_path.split('.')[-1] == 'png' or folder_path.split('.')[-1] == 'txt':
        pass
    files = get_files_with_path(folder_path)

    T = int(np.round(float(folder_path.split('_')[5]),0))
    
    fig.suptitle(f'{T} K')
    max = []
    marker = marker_l()
    for i in files:
        off = (i.split('_')[-2]).split('.')[0]
        data = np.genfromtxt(i, unpack=True, delimiter=',')
        time = data[0]
        mk = next(marker)
        ax1.plot(data[0], data[1],markerfacecolor=None, marker= mk, label=str(off) +'mV')
        ax2.plot(data[0], data[3],markerfacecolor=None, marker= mk, label=str(off)+ 'mV')
        name = str(folder_path.split('_')[5]) +'K'
        max.append(np.nanmax(data[1]))
        # plt.text(14, 1.75, 'HRS', color='blue', fontsize=11)
        # plt.text(25, 1.0, 'Transición', color='grey', fontsize=11)
        # plt.text(14, 0.2, 'LRS', color='red', fontsize=11)
        # if int(off)==0:
        #     plt.fill_between(data[0], data[1][2]+0.1, data[1][2]-0.1, color='blue', alpha=0.15)
        # if int(off)==200:
        #     plt.fill_between(data[0], data[1][2]+0.3, data[1][2]-0.1, color='red', alpha=0.15)
        # if (int(off)==0 or int(off)==200):
        #     plt.fill_between(data[0], data[1]+0.3, data[1]-0.1, color='blue', alpha=0.3, label='Region')    
    # ax1.set_ylim(-0.1,np.nanmax(max)*1.1)
    # ax1.set_ylim(-0.1,3)
    ax1.set_ylabel('R ($\Omega$)')
    ax1.set_xlabel('Frecuencia (Hz)')
    ax2.set_xscale('log')
    ax2.set_ylabel('X')

    ax1.grid()
    ax2.grid()
    handles1, labels1 = ax1.get_legend_handles_labels()
    ax2.legend(handles1, labels1, loc='center left', bbox_to_anchor=(1, 0))
    # Adjust layout to make room for the legend
    # plt.title(name)
    #plt.tight_layout()

    plt.savefig(f'{folder_path} {name}.png')
    # plt.show()
    # plt.close()
# 

data[1]

# Commented out IPython magic to ensure Python compatibility.
#%%
from scipy.integrate import simpson, trapezoid
import scipy as sp
for fi in [1, 8, 12, 18, 22, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, -1]:
    fig, (ax1, ax2, ax3) = plt.subplots(3,1, figsize=(5,8), sharex=True)
    marker = marker_l()
    for a in [
    'ZdeW_1234_Temperatura_85.12_K_1236',
    'ZdeW_1234_Temperatura_100.22_K_1407',
    #'ZdeW_1234_Temperatura_120.19_K_1544',
    'ZdeW_1234_Temperatura_140.37_K_1719',
    'ZdeW_1234_Temperatura_160.35_K_1854',
    #'ZdeW_1234_Temperatura_180.48_K_2029',
    'ZdeW_1234_Temperatura_200.58_K_2214',
    'ZdeW_1234_Temperatura_220.53_K_0040',
    #'ZdeW_1234_Temperatura_240.62_K_0217',
    'ZdeW_1234_Temperatura_260.74_K_0356',
    'ZdeW_1234_Temperatura_280.79_K_0534',
    ]:
        X = []
        Y = []
        Z = []
        xplot = []
#         %matplotlib qt
        yplot = []
        dirs = "E:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
        fil = list_folders_in_folder(dirs)
        for j in [1]:
            j = a
            folder_path = dirs+j
            if folder_path.split('.')[-1] == 'png' or folder_path.split('.')[-1] == 'txt':
                pass
            files = get_files_with_path(folder_path)
            for i in files:
                data = np.genfromtxt(i, unpack=True, delimiter=',')
                f = data[0][fi]
                R = data[1][fi]
                X = data[3][fi]
                Z = np.sqrt(R**2 + X**2)
                theta = np.arctan(X/R)
                Vdc = (i.split('_')[-2]).split('.')[0]
                xplot.append(float(Vdc))
                yplot.append(float(R))
        fig.suptitle(f'K freq = {f}')
        xplot = np.array(xplot)
        yplot = np.array(yplot)
        mk = next(marker)
        idx_order =  np.argsort(xplot)
        xplot = xplot[idx_order]
        yplot = yplot[idx_order]
        ax1.plot(xplot, yplot, marker=mk, markersize=8, alpha=0.7, linewidth=0.5, linestyle='--')
        ax1.set_ylabel('Re(Z) [Ohm]')
        ax1.grid(True)
        ax2.plot(xplot, 1/yplot, marker=mk, markersize=8, alpha=0.7, linewidth=0.5, linestyle='--')
        ax2.set_ylabel('1/Re(Z)')
        ax2.grid(True)
        yint = sp.integrate.cumulative_trapezoid(yplot, xplot, initial=0)
        ax3.plot(xplot, yint, marker=mk, markersize=8, alpha=0.7, linewidth=0.5, linestyle='--')
        ax3.set_ylabel('$\int{1/Re(Z)(V_{dc}) dV_{dc}}$')
        ax3.set_xlabel('Offset (V)')
        ax3.grid(True)
        ax1.legend()
        plt.tight_layout()
    plt.savefig(f'{a} {f}.png')
plt.show()
#%%
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(5, 7))
dirs = "e:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
fil = list_folders_in_folder(dirs)
marker = marker_l()
for j in fil:
    folder_path = dirs+j
    if folder_path.split('.')[-1] == 'png' or folder_path.split('.')[-1] == 'txt':
        pass
    files = get_files_with_path(folder_path)
    fig.suptitle('X5 $V_{dc}=0$')

    for i in files:
        if float((i.split('_')[-2]).split('.')[0])>0.00:
            break
        data = np.genfromtxt(i, unpack=True, delimiter=',')
        f = data[0][1:]
        R = data[1][1:]
        X = data[3][1:]
        Z = np.sqrt(R**2 + X**2)
        theta = np.arctan(X/R)
        time = data[0]
        mk = next(marker)
        ax1.plot(f, Z, markerfacecolor=None, marker= mk, label=f'{folder_path.split('_')[5]} K')
        ax2.plot(f, theta, markerfacecolor=None, marker= mk, label=f'{folder_path.split('_')[5]} K')
        #if n == True:
        #    ax1.set_ylim(np.min(data[1]),np.max(data[1][1:]))
        #    n = False
        #name = f'{folder_path.split('_')[4]} K'
    ax1.set_ylabel('Z ($\Omega$)')
    ax2.set_xlabel('f (Hz)')
    ax2.set_xscale('log')
    ax1.set_xscale('log')
    #ax1.set_yscale('log')
    ax2.set_ylabel('$\\theta$')
    ax1.grid(True)
    ax2.grid(True)
    #ax2.legend()
    # Adjust layout to make room for the legend
    plt.tight_layout()

plt.show()
#%% Analisis de rampas individuales
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
dirs = "E:/porno/tesis 3/tesisfisica/IVs/912/"
for i in list_folders_in_folder(dirs):
    fig, axs = plt.subplots(2, 2, figsize=(9, 5), sharex=True)
    marker = marker_l()
    folder_path = dirs+i
    ramp = get_files_with_path(folder_path)
    data = np.genfromtxt(ramp[0], unpack=True, delimiter=',')
    fig.suptitle('Rampa T $V_{dc}$'+f'$={data[11][10]}$'+'$V_{ac}$'+f'$={data[10][10]}$')
    time = data[0][1:]
    T = data[2][1:]
    norm = mcolors.Normalize(vmin=min(time), vmax=max(time))
    cmap = plt.cm.viridis 
    Z40 = data[5][1:]
    t40 = data[6][1:]
    R40 = Z40*np.cos(t40*np.pi/180)
    X40 = t40*np.sin(t40*np.pi/180)
    Z200k = data[7][1:]
    t200k = data[8][1:]
    R200k = Z200k*np.cos(t200k*np.pi/180)
    X200k = t200k*np.sin(t200k*np.pi/180)
    sc1 = axs[0, 0].scatter(T, X40, c=time, cmap=cmap, norm=norm, label=f'40 Hz')
    sc2 = axs[0, 1].scatter(T, X200k, c=time, cmap=cmap, norm=norm, label=f'200 kHz')
    sc3 = axs[1, 0].scatter(T, R40, c=time, cmap=cmap, norm=norm, label=f'40 Hz')
    sc4 = axs[1, 1].scatter(T, R200k, c=time, cmap=cmap, norm=norm, label=f'200 kHz')
    axs[0,0].set_ylabel('X ($\Omega$)')
    axs[0,0].set_yscale('log')
    axs[1,1].set_xlabel('T (K)')
    axs[1,0].set_xlabel('T (K)')
    axs[1,0].set_ylabel('R ($\Omega$)')
    # axs[1,0].set_yscale('asinh')
    # axs[0,1].set_yscale('asinh')
    # axs[1,1].set_yscale('asinh')
    axs[0,0].grid(True)
    axs[1,0].grid(True)
    axs[0,1].grid(True)
    axs[1,1].grid(True)
    axs[0,0].legend()
    axs[0,1].legend()
    axs[1,0].legend()
    axs[1,1].legend()
    plt.tight_layout()
    plt.subplots_adjust(right=0.85)  # Move subplots left, e.g. 0.85 or 0.8

    # Now place a single colorbar for all subplots
    cbar = fig.colorbar(
        sc1,                            # or whichever scatter you like
        ax=axs.ravel().tolist(),        # attach it to all subplots
        location='right',
        fraction=0.05,                  # width of the colorbar relative to the figure
        pad=0.04                        # gap between colorbar and subplots
    )
    cbar.set_label('Tiempo (s)')

    plt.savefig('RampaTenLCRRX $V_{dc}$'+f'$={data[11][10]}$.png')
    fig, axs = plt.subplots(2, 2, figsize=(9, 5), sharex=True)
    fig.suptitle('Rampa T $V_{dc}$'+f'$={data[11][10]}$'+'$V_{ac}$'+f'$={data[10][10]}$')
    time = data[0][1:]
    T = data[2][1:]
    norm = mcolors.Normalize(vmin=min(time), vmax=max(time))
    cmap = plt.cm.viridis  # You can change the colormap here
    Z40 = data[5][1:]
    t40 = data[6][1:]
    R40 = Z40*np.cos(t40*np.pi/180)
    X40 = t40*np.sin(t40*np.pi/180)
    Z200k = data[7][1:]
    t200k = data[8][1:]
    R200k = Z200k*np.cos(t200k*np.pi/180)
    X200k = t200k*np.sin(t200k*np.pi/180)
    sc1 = axs[0, 0].scatter(T, t40, c=time, cmap=cmap, norm=norm, label=f'40 Hz')
    sc2 = axs[0, 1].scatter(T, t200k, c=time, cmap=cmap, norm=norm, label=f'200 kHz')
    sc3 = axs[1, 0].scatter(T, Z40, c=time, cmap=cmap, norm=norm, label=f'40 Hz')
    sc4 = axs[1, 1].scatter(T, Z200k, c=time, cmap=cmap, norm=norm, label=f'200 kHz')
    axs[0,0].set_ylabel('$\\theta$')
    axs[1,1].set_xlabel('T (K)')
    axs[1,0].set_xlabel('T (K)')
    axs[1,0].set_ylabel('|Z| ($\Omega$)')
    # axs[1,0].set_yscale('asinh')
    # axs[1,1].set_yscale('asinh')
    axs[0,0].grid(True)
    axs[1,0].grid(True)
    axs[0,1].grid(True)
    axs[1,1].grid(True)
    axs[0,0].legend()
    axs[0,1].legend()
    axs[1,0].legend()
    axs[1,1].legend()
    plt.tight_layout()
    plt.subplots_adjust(right=0.85)  # Move subplots left, e.g. 0.85 or 0.8

    # Now place a single colorbar for all subplots
    cbar = fig.colorbar(
        sc1,                            # or whichever scatter you like
        ax=axs.ravel().tolist(),        # attach it to all subplots
        location='right',
        fraction=0.05,                  # width of the colorbar relative to the figure
        pad=0.04                        # gap between colorbar and subplots
    )
    cbar.set_label('Tiempo (s)')

    plt.savefig('RampaTenLCRZT $V_{dc}$'+f'$={data[11][10]}$.png')
#%% Analisis de pares de rampas

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
%matplotlib qt
colors = [
    '#1f77b4',  # Blue
    '#ff7f0e',  # Orange
    '#2ca02c',  # Green
    '#d62728',  # Red
    '#9467bd',  # Purple
    '#8c564b',  # Brown
    '#e377c2',  # Pink
    '#7f7f7f',  # Gray
    '#bcbd22',  # Olive
    '#17becf',  # Cyan
    '#aec7e8',  # Light Blue
    '#ffbb78',  # Light Orange
    '#98df8a',  # Light Green
    '#ff9896'   # Light Red
]

dirs2 = get_files_with_path('e:\porno/tesis 3/tesisfisica\IVs/rampasT-ZdeW')
dirs = []
for i in dirs2:
    if 'txt' in i:
        dirs.append(i)
fig, axs = plt.subplots(2, 2, figsize=(9, 7), sharex=True)
s=10
n = 0
for i in dirs:
    data = np.genfromtxt(i, unpack=True, delimiter=',')
    time = data[0][1:]
    T = data[2][1:]
    Z40 = data[5][1:]
    t40 = data[6][1:]
    Z200k = data[7][1:]
    t200k = data[8][1:]
    R40 = Z40*np.cos(t40*np.pi/180)
    X40 = t40*np.sin(t40*np.pi/180)
    R200k = Z200k*np.cos(t200k*np.pi/180)
    X200k = t200k*np.sin(t200k*np.pi/180)
    vac, vdc = data[-5][10], data[-4][10]
    if np.min(T)>50 and '_08-12-24b_' not in i:
        sc1 = axs[0, 0].scatter(T, X40, color=colors[n], s=7, label=f'{i.split("_")[1].split('-')[0]}.{i.split("_")[1].split('-')[1]}' + ' $V_{ac}$='+str(vac)+' mV $V_{dc}$=' +str(vdc)+ ' mV') 
        sc2 = axs[0, 1].plot(T, X200k, color=colors[n])
        sc3 = axs[1, 0].plot(T, R40, color=colors[n])
        sc4 = axs[1, 1].plot(T, R200k, color=colors[n])
    else:
        sc1 = axs[0, 0].scatter(T, X40, color=colors[n], s=7, label=f'{i.split("_")[1].split('-')[0]}.{i.split("_")[1].split('-')[1]}' + ' $V_{ac}$='+str(vac)+' mV $V_{dc}$=' +str(vdc)+ ' mV') 
        sc2 = axs[0, 1].scatter(T, X200k, s=7, color=colors[n])
        sc3 = axs[1, 0].scatter(T, R40, s=7, color=colors[n])
        sc4 = axs[1, 1].scatter(T, R200k, s=7, color=colors[n])
    n+=1
axs[0,0].set_ylabel('X ($\Omega$)')
axs[1,1].set_xlabel('T (K)')
axs[1,0].set_xlabel('T (K)')
axs[1,0].set_ylabel('R ($\Omega$)')
axs[0,0].grid(True)
axs[1,0].grid(True)
axs[0,1].grid(True)
axs[1,1].grid(True)
# fig.legend(loc='upper center', bbox_to_anchor=(0.5, 1),
        #   ncol=3, fancybox=True, fontsize=8, framealpha=1)
# axs[0,1].legend()
# axs[1,0].legend()
# axs[1,1].legend()
axs[0,0].set_ylim(0,150)
axs[1,0].set_ylim(0,100)
axs[1,1].set_ylim(-500,500)
axs[0,0].set_yscale('symlog', linthresh=1e-1)
axs[1,0].set_yscale('symlog', linthresh=1e0)
axs[1,1].set_yscale('symlog', linthresh=1e-1)
plt.tight_layout()
# cbar = fig.colorbar(
#     sc1,                            # or whichever scatter you like
#     ax=axs.ravel().tolist(),        # attach it to all subplots
#     anchor=(-0.75,0),
#     pad=0,
#     ticks=([0,1])
# )
# cbar.set_label('Tiempo (s)')
# cbar = fig.colorbar(
#     cm.ScalarMappable(norm=norm, cmap=plt.cm.viridis),                            # or whichever scatter you like
#     ax=axs.ravel().tolist(),        # attach it to all subplots
#     location='right',
#     ticks=([])
# )

# plt.savefig(f'E:/porno/tesis 3/tesisfisica/IVs/rampasT-ZdeW/RampaTenLCRRX.png')
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
# fig.legend(loc='upper center', bbox_to_anchor=(0.5,1),
#           ncol=3, fancybox=True, fontsize=8, framealpha=0.5)
# axs[0,1].legend()
# axs[1,0].legend()
# axs[1,1].legend()
axs[1,0].set_yscale('symlog')
axs[1,1].set_yscale('symlog')
axs[1,0].set_ylim(0,100)
# axs[1,1].set_ylim(-1,50)
plt.tight_layout()
# cbar = fig.colorbar(
#     sc1,                            # or whichever scatter you like
#     ax=axs.ravel().tolist(),        # attach it to all subplots
#     anchor=(-0.75,0),
#     pad=0,
#     ticks=([0,1])
# )
# cbar.set_label('Tiempo (s)')
# cbar = fig.colorbar(
#     cm.ScalarMappable(norm=norm, cmap=plt.cm.viridis),                            # or whichever scatter you like
#     ax=axs.ravel().tolist(),        # attach it to all subplots
#     location='right',
#     ticks=([])
# )
# plt.savefig(f'E:/porno/tesis 3/tesisfisica/IVs/rampasT-ZdeW/RampaTenLCRZT.png')


# %%
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
dirs = "E:/porno/tesis 3/tesisfisica/IVs/rampasT-ZdeW/"
for i in get_files_with_path(dirs):
    data = np.genfromtxt(i, unpack=True, delimiter=',', skip_header=1)
    print(i.split('_')[1],',',data[10][0], ',', data[11][0])
# %%
