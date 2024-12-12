#%%
import numpy as np
import matplotlib.pyplot as plt
import os
import itertools
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
    return [os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]
#%%
# Example usage
%matplotlib qt
dirs = "C:/tesis git/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
fil = list_folders_in_folder(dirs)
fig, (ax2, ax1) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
fig.suptitle('$V_{dc}=0$ mV $V_{ac}=100$ mV')
for j in fil:
    folder_path = dirs+j
    if folder_path.split('.')[-1] == 'png' or folder_path.split('.')[-1] == 'txt':
        pass
    files = get_files_with_path(folder_path)
    n = True
    marker = marker_l()
    for i in files:
        if float(i.split('_')[-2])>0.00:
            break
        data = np.genfromtxt(i, unpack=True, delimiter=',')
        time = data[0]
        mk = next(marker)
        ax1.plot(data[0], data[1],markerfacecolor=None, marker= mk, label=f'{folder_path.split('_')[5]} K')
        ax2.plot(data[0], data[3],markerfacecolor=None, marker= mk, label=f'{folder_path.split('_')[5]} K')
        if n == True:
            ax1.set_ylim(-0.1,np.max(data[1][1:]))
            n = False
        name = f'{folder_path.split('_')[4]} K'
    ax1.set_ylabel('R ($\Omega$)')
    ax2.set_xlabel('Frecuencia (Hz)')
    ax2.set_xscale('log')
    ax2.set_ylabel('X')
    ax1.set_xscale('log')

    ax1.grid(True)
    ax2.grid(True)
    handles1, labels1 = ax1.get_legend_handles_labels()
    ax2.legend(handles1, labels1, loc='center left', bbox_to_anchor=(1, 0))
#plt.tight_layout()
plt.savefig(f'{folder_path} {name} dc0 ac100.png')
plt.show()
# %%
