#%%
import matplotlib.pyplot as plt
import numpy as np
import os
def get_files_with_path(folder):
    print(folder)
    return [os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]
dirs = ['./Archivos/X5/rampas', './Archivos/X6/rampas']
rampas = get_files_with_path(dirs[0])
fig, ax = plt.subplots(figsize=(6, 5), dpi=150)
for filename in rampas:
    try:
        T, s, h, v1, i1, r1, v2, i2, r2 = np.genfromtxt(filename, usecols=(1,2,3,4,5,6,7,8,9), delimiter=',', unpack=True, skip_header=1)
    # Only keep values where i1 == 0.001
        # mask = np.isclose(i1, 0.0001)
        # T, r1 = T[mask], r1[mask]
    except:
        t, T, s, h, r1, r2 = np.genfromtxt(filename, delimiter=',', unpack=True, skip_header=1)
    if filename == './Archivos/X5/rampas\\RampaRdeT711.csv':
        r1 = r1[:]
        filename = './Archivos/X5/rampas\\RampaRdeT7-11.csv'
        cor = "#4A85F1"
        continue
    elif filename == './Archivos/X5/rampas\\RampaRdeT811.csv':
        r1 = r1[:1512]
        T = T[:1512]
        filename = './Archivos/X5/rampas\\RampaRdeT8-11 (I=1 mA).csv'
        cor = '#F1B74A'
        # print('8-11')
        # print(r1[:5])
        continue
    elif filename == './Archivos/X5/rampas\\RampaRdeT1212.csv':
        r1 = r1[:1850]
        T = T[:1850]
        filename = './Archivos/X5/rampas/RampaRdeT12-12.csv'
        filename = './Archivos/X5/rampas/RampaRdeT1212 (I=1 mA).csv'
        # pass
        cor = '#F1B74A'
        # continue
    elif filename == './Archivos/X5/rampas\\RampaRdeT1212 I=10 mA.csv':
        # r1 = r1[1890:]
        # T = T[1890:]
    # #     cor = '#E63946'
        continue
    elif filename == './Archivos/X5/rampas\\RampaRdeT1312 I=0,1 mA.csv':
        filename = './Archivos/X5/rampas\\RampaRdeT13-12 (I=0,1 mA).csv'
        # pass
        r1 = r1[:]
        T = T[:]
        cor = "#4A85F1"
        # continue
    elif filename == './Archivos/X5/rampas\\RampaRdeT1712b.csv':
        filename = './Archivos/X5/rampas\\RampaRdeT17-12.csv'
        cor = '#E63946'
        # pass
        continue
    elif filename == './Archivos/X5/rampas\\RampaRdeT1812.csv':
        filename = './Archivos/X5/rampas\\RampaRdeT18-12.csv'
        cor = "#4A85F1"
        # pass
        continue
    try: 
        ax.scatter(T, r1, c=cor, s=10, label=f'{filename.split("/")[2]+' '+filename.split("\\")[-1].split("T")[-1].split('.')[0]}')
    except Exception as e:
        print(e)
        continue
    #dividir por 41 la r  
rampas = get_files_with_path(dirs[1])
for filename in rampas:
    try:
        T, s, h, v1, i1, r1, v2, i2, r2 = np.genfromtxt(filename, usecols=(1,2,3,4,5,6,7,8,9), delimiter=',', unpack=True, skip_header=1)
        # Plot for i1 == 0.001
        mask_1mA = np.isclose(i1, 0.001)
        if np.any(mask_1mA):
            T_1mA, r1_1mA = T[mask_1mA], r1[mask_1mA]
            # Remove the tail of the file name after 'rampas\\Rampa'
            base_name = filename.split("rampas\\Rampa")[-1].split('.')[0]
            ax.scatter(T_1mA[:-200], r1_1mA[:-200], c="#4AF19D", s=10, label=f'{base_name} (I=1mA)')
        # Plot for i1 == 0.0001
        mask_0_1mA = np.isclose(i1, 0.0001)
        if np.any(mask_0_1mA):
            T_0_1mA, r1_0_1mA = T[mask_0_1mA], r1[mask_0_1mA]
            base_name = filename.split("rampas\\Rampa")[-1].split('.')[0]
            ax.scatter(T_0_1mA, r1_0_1mA, c="#F14AE9", s=10, label=f'{base_name} (I=0,1mA)')
    except Exception as e:
        print(e)
        continue
    #dividir por 0.36 la r  
# xdeox = np.array([1, 10, 40, 50, 60, 70, 80, 90, 100, 105, 110, 120, 135, 150, 200, 250, 300])
# ydeox = np.array([4e-2, 3.8e-2, 3.8e-2, 4e-2, 4.2e-2, 6e-2, 1e-1, 1.3e-1, 1.47e-1, 1.5e-1, 1.47e-1, 1.41e-1, 1.2e-1, 1.1e-1, 9e-2, 8e-2, 7.5e-2])
# mk = next(marker)
# mk='o'
# ax.plot(xdeox, ydeox, marker=mk, label='Qi $\delta$ ~ 0.04 $\\rho_c$ ', color='black')
# xdeox = np.array([1, 10, 40, 50, 60, 70, 100, 130, 160, 200, 250, 300])
# ydeox = np.array([1e-5, 2e-5, 1e-3, 2e-3, 3e-3, 4e-3, 2e-2, 3e-2, 2.6e-2, 1.6e-2, 1e-2, 0.8e-2])
# mk = next(marker)
# ax.plot(xdeox, ydeox, marker=mk, label='Qi $\delta$ ~ 0.04 $\\rho_a$ I=0.05mA', color='blue')
# ax.set_yscale('symlog')
# ax2.set_yscale('symlog')
# ticks = np.array([0e-2, 2e-2, 4e-2, 6e-2, 8e-2, 1e-1, 1.2e-1, 1.4e-1, 1.6e-1, 1.8e-1, 2e-1, 2.2e-1, 2.4e-1, 2.6e-1])
# ax.set_yticks([0e-2, 2e-2, 4e-2, 6e-2, 8e-2, 1e-1, 1.2e-1, 1.4e-1, 1.6e-1, 1.8e-1, 2e-1, 2.2e-1, 2.4e-1, 2.6e-1])
# ax2.set_yticks([0,1,2,3,4,5,6,7,8])
# ax.set_ylim(-0.01,0.21)
# ax2.set_ylim(-0.4,8.4)
# ax2.set_ylabel('R ($\Omega$)')
# ax.set_xlabel('T (K)')
# ax.set_ylabel('$\\rho$ ($\Omega$ cm)')
# ax.set_xlim(8, 100)
# ax2.set_ylabel('R ($\Omega$)')
# plt.suptitle(f'Resistividad 4 terminales, I = 1 mA')
ax.set_xlabel('T (K)')
ax.set_ylabel('R ($\Omega$)')
ax.set_yscale('log')
ax.legend()
ax.grid()
plt.show()
# %%
