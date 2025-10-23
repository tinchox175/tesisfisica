#%%
import numpy as np
import matplotlib.pyplot as plt
import os
import itertools
from natsort import natsorted
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
    # print(folder)
    return [os.path.join(folder, file) for file in natsorted(os.listdir(folder)) if os.path.isfile(os.path.join(folder, file))]
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]
#%%
# Example usage
dirs = "e:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
fil = list_folders_in_folder(dirs)
# import matplotlib
# matplotlib.rcParams['figure.figsize'] = [10, 10]
import matplotlib
matplotlib.rcParams['font.size'] = 14
for j in fil:
    folder_path = dirs+j
    if folder_path.split('.')[-1] == 'png' or folder_path.split('.')[-1] == 'txt':
        pass
    files = get_files_with_path(folder_path)
    if folder_path.split('_')[5].split('.')[0] == '100':
        pass
    else:
        continue
    print(folder_path.split('_')[5].split('.')[0])
    fig, (ax1) = plt.subplots(1, 1, figsize=(4, 4), dpi=300, sharex=True, gridspec_kw={'width_ratios': [0.8]})
    # fig.suptitle(f'{folder_path.split('_')[5]} K')
    n = True
    marker = marker_l()
    minr = 100
    maxr = 0
    minx = 100
    maxx = 0
    n=0
    for i in files:
        if 'eis' in i:
            continue
        # if float((i.split('_')[-2]).split('.')[0])==0.0:
        #     print(0)
        #     pass
        # elif float((i.split('_')[-2]).split('.')[0])==10.0:
        #     print(10)
        #     pass
        # else:
        #     continue
        dc = (i.split('_')[-2]).split('.')[0]
        # print(dc)
        data = np.genfromtxt(i, unpack=True, delimiter=',')
        time = data[0]
        mk = next(marker)
        y1 = data[1][:]
        y2 = data[3][:]
        x = data[0][:]
        # Update min/max for y1 (ax1)
        # cur_minr = np.min(y1)
        # cur_maxr = np.max(y1)
        # if cur_minr < minr:
        #     minr = cur_minr
        # if cur_maxr > maxr:
        #     maxr = cur_maxr
        # # Update min/max for y2 (ax2)
        # cur_minx = np.min(y2)
        # cur_maxx = np.max(y2)
        # if cur_minx < minx:
        #     minx = cur_minx
        # if cur_maxx > maxx:
        #     maxx = cur_maxx
        ax1.plot(x, y1, markerfacecolor=None, marker=mk, label=f'{(i.split("_")[-2]).split(".")[0]} mV')
        # ax2.plot(x, y2, markerfacecolor=None, marker=mk, label=f'{(i.split("_")[-2]).split(".")[0]} mV')
        name = f'{folder_path.split("_")[5]} K'
        if n==1:
            break
        else:
            n += 1
    # Set axis limits after plotting all curves
    ax1.set_ylim(-2.3,  4)
    # ax2.set_ylim(minx - abs(minx) * 0.1, maxx * 1.2)
    ax1.set_ylabel('Z\' ($\Omega$)')
    ax1.set_xlabel('Frecuencia (Hz)')
    ax1.set_xscale('log')
    # ax2.set_ylabel('Z\'\' ($\Omega$)')

    ax1.grid()
    # ax2.grid()
    handles1, labels1 = ax1.get_legend_handles_labels()
    ax1.legend()
    # Adjust layout to make room for the legend
    # plt.tight_layout()
    # print(folder_path.split('_')[5])
    # break
    # plt.savefig(f'{folder_path} {name}.png', dpi=300)
    # break
    #plt.close()
plt.show()
#%% UNA CELDA IDENTICA AL DE ARRIBA#############################################################################
# Example usage
dirs = "e:/porno/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
fil = list_folders_in_folder(dirs)
fig, (ax2, ax1) = plt.subplots(2, 1, figsize=(6, 3), dpi=300, sharex=True)
for j in natsorted(fil)[::3]:
    folder_path = dirs+j
    if folder_path.split('.')[-1] == 'png' or folder_path.split('.')[-1] == 'txt':
        pass
    files = get_files_with_path(folder_path)
    T = folder_path.split('_')[5].split('.')[0]
    # fig.suptitle(f'{folder_path.split('_')[5]} K')
    n = True
    marker = marker_l()
    minr = 100
    maxr = 0
    minx = 100
    maxx = 0
    for i in files:
        dc = (i.split('_')[-2]).split('.')[0]
        if dc in ['0']:
            pass
        else:
            continue
        data = np.genfromtxt(i, unpack=True, delimiter=',')
        time = data[0]
        mk = next(marker)
        ax1.plot(data[0][2:-1], data[1][2:-1],markerfacecolor=None, marker= mk, label=f'{T} K')
        ax2.plot(data[0][2:-1], data[3][2:-1],markerfacecolor=None, marker= mk, label=f'{T} K')
        if n == True:
            newminx = np.min(data[3][2:-1])
            newmaxx = np.max(data[3][2:-1])
            newminr = np.min(data[1][2:-1])   
            newmaxr = np.max(data[1][2:-1])
            if  newminx < minx:
                minx = np.min(data[3][2:-1])
                ax1.set_ylim(minr*0.99,maxr*1.1)
                ax2.set_ylim(minx-abs(minx)*0.7,maxx*1.1)
            if  newmaxx > maxx:
                maxx = np.max(data[3][2:-1])
                ax1.set_ylim(minr*0.99,maxr*1.1)
                ax2.set_ylim(minx-abs(minx)*0.7,maxx*1.1)
            if newminr < minr:
                minr = np.min(data[1][2:-1])
                ax1.set_ylim(minr*0.99,maxr*1.1)
                ax2.set_ylim(minx-abs(minx)*0.7,maxx*1.1)
            if newmaxr > maxr:
                maxr = np.max(data[1][2:-1])
                ax1.set_ylim(minr*0.99,maxr*1.1)
                ax2.set_ylim(minx-abs(minx)*0.7,maxx*1.1)
ax1.set_ylim(0,150)
ax2.set_ylim(minx-3,30+6)
name = f'{folder_path.split('_')[5]} K'
ax1.set_ylabel('Z\' ($\Omega$)')
ax1.set_xlabel('Frecuencia (Hz)')
ax2.set_xscale('log')
ax2.set_ylabel('Z\'\' ($\Omega$)')

ax1.grid()
ax2.grid()
handles1, labels1 = ax1.get_legend_handles_labels()
ax2.legend(handles1, labels1, loc='center left', bbox_to_anchor=(1, 0))
    # Adjust layout to make room for the legend
    # plt.tight_layout()
    
    # plt.savefig(f'{folder_path} {name}.png')
    #plt.close()
plt.show()
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
        %matplotlib qt
        yplot = []
        dirs = "e:/porno/tesis 3/tesis git/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
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
        ax1.plot(xplot, yplot, label=f'{folder_path.split('_')[5]} K', marker=mk, markersize=8, alpha=0.7, linewidth=0.5, linestyle='--')
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
    # plt.savefig(f'{a} {f}.png')
plt.show()
# %%
#%%
# Example usage
%matplotlib qt
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(5, 7))
dirs = "e:/porno/tesis 3/tesis git/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
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
    
plt.savefig(f'X5.png')
plt.show()
# %%
