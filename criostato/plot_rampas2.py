#%%
import matplotlib.pyplot as plt
import numpy as np
import os
import matplotlib as mpl
import matplotlib.ticker as ticker
mpl.rcParams.update({
    'font.size': 5.5,
    'axes.titlesize': 16,
    'axes.labelsize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 10
})

def get_files_with_path(folder):
    print(folder)
    return [os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]
dirs = ['./Archivos/X5/rampas', './Archivos/X6/rampas']
rampas = get_files_with_path(dirs[0])
fig, ax = plt.subplots(figsize=(4, 3), dpi=450)
# fig.patch.set_facecolor('#e3eeffff')
rampas = ['./Archivos/X5/rampas\\RampaRdeT1212 I=10 mA.csv',
 './Archivos/X5/rampas\\RampaRdeT1212.csv',
 './Archivos/X5/rampas\\RampaRdeT1712b.csv',
 './Archivos/X5/rampas\\RampaRdeT1812.csv',
 './Archivos/X5/rampas\\RampaRdeT711.csv',
 './Archivos/X5/rampas\\RampaRdeT1312 I=0,1 mA.csv',
 './Archivos/X5/rampas\\RampaRdeT811.csv']
for filename in rampas:
    try:
        T, s, h, v1, i1, r1, v2, i2, r2 = np.genfromtxt(filename, usecols=(1,2,3,4,5,6,7,8,9), delimiter=',', unpack=True, skip_header=1)
    # Only keep values where i1 == 0.001
        # mask = np.isclose(i1, 0.0001)
        # T, r1 = T[mask], r1[mask]
    except:
        t, T, s, h, r1, r2 = np.genfromtxt(filename, delimiter=',', unpack=True, skip_header=1)
    if filename == './Archivos/X5/rampas\\RampaRdeT711.csv':
        continue
        r1 = r1[:]
        filename = './Archivos/X5/rampas\\RampaRdeT7-11.csv'
        cor = "#F14A74"
        continue
    elif filename == './Archivos/X5/rampas\\RampaRdeT1212 I=10 mA.csv':
        continue
        filename = 'X1b $I=10.0$ mA'
        rc = r1[:400]
        Tc = T[:400]
        rc2 = r1[1900:]
        Tc2 = T[1900:]
        r1 = np.concatenate((rc, rc2))
        T = np.concatenate((Tc, Tc2))
        cor = "#E639AC"
        # continue
    elif filename == './Archivos/X5/rampas\\RampaRdeT811.csv':
        # continue
        r1 = r1[:1571]
        T = T[:1571]
        filename = 'X1a'
        cor = "#47C0B0"
        # print('8-11')
        # print(r1[:5])
        r1 = np.concatenate((r1[:672],r1[672:772]*0.92,r1[772:-1]*0.9))
    elif filename == './Archivos/X5/rampas\\RampaRdeT1212.csv':
        continue
        r1 = r1[:1850]
        T = T[:1850]
        filename = './Archivos/X5/rampas/RampaRdeT12-12.csv'
        filename = './Archivos/X5/rampas/RampaRdeT1212 (I=1 mA).csv'
        # pass
        cor = "#4AD0F1"
    elif filename == './Archivos/X5/rampas\\RampaRdeT1312 I=0,1 mA.csv':
        continue
        filename = 'X1b $I=0.1$ mA'
        # pass
        r1 = r1[:]
        T = T[:]
        # smooth r1 with a moving-average filter
        window = 27  # must be odd; increase for stronger smoothing
        if window % 2 == 0:
            window += 1
        if r1.size >= window:
            kernel = np.ones(window) / window
            r1 = np.convolve(r1, kernel, mode='same')[15:-10]
        cor = "#F1A34A"
        T = T[15:-10]
        r1 = np.flip(r1)
        T = np.flip(T)
        # continue
    elif filename == './Archivos/X5/rampas\\RampaRdeT1712b.csv':
        # continue
        filename = 'X1b'
        cor = '#E63946'
        # pass
        # continue
    elif filename == './Archivos/X5/rampas\\RampaRdeT1812.csv':
        continue
        filename = './Archivos/X5/rampas\\RampaRdeT18-12.csv'
        cor = "#4883F1"
        # pass
        continue
    if '#47C0B0' in cor and '10' not in filename:
        targets = np.arange(0,300,6)
        indices = [np.abs(T - q).argmin() for q in targets]
        try:
            print(filename)
            print(T)
            print(indices)
            print(r1/41)
            if "#47C0B0" not in cor:
                ax.scatter(T[indices], r1[indices]/41, edgecolors=cor, facecolors='none', marker='o', s=10, label=f'{filename}')
                # ax.scatter(T[indices2], r1[indices2]/41, edgecolors=cor, facecolors='none', marker='o', s=10)
            else:
                ax.scatter(T[indices], r1[indices]/41, edgecolors=cor, facecolors='none', marker='o', s=10, label=f'{filename}')
                # ax.scatter(T[indices2], r1[indices2]/41, edgecolors=cor, facecolors='none', marker='o', s=10)
        except Exception as e:
            print(e)
            continue
    if '10' not in filename and '#47C0B0' not in cor:
        targets1 = np.arange(100,300,7)
        targets2 = np.arange(45,100,6)
        targets = np.concatenate((targets1, targets2))
        indices = [np.abs(T - q).argmin() for q in targets]
        indices2 = [np.abs(r1/41 - q).argmin() for q in np.arange(0.09, 0.2, 0.005)]
        # ax.vlines([10,25,50,100,300], ymin=0, ymax=[0.2,0.2,0.2,0.2,0.2], colors='gray', linestyles='dashed', linewidth=0.5)
        try:
            print(filename)
            print(T)
            print(indices)
            print(r1/41)
            if "#47C0B0" not in cor:
                ax.scatter(T[indices], r1[indices]/41, edgecolors=cor, facecolors='none', marker='o', s=10, label=f'{filename}')
                ax.scatter(T[indices2], r1[indices2]/41, edgecolors=cor, facecolors='none', marker='o', s=10)
            else:
                ax.scatter(T[indices], r1[indices]/41, edgecolors=cor, facecolors='none', marker='o', s=10, label=f'{filename}')
                ax.scatter(T[indices2], r1[indices2]/41, edgecolors=cor, facecolors='none', marker='o', s=10)
        except Exception as e:
            print(e)
            continue
    elif '10' in filename:
        targets = np.arange(0,300,6)
        indices = [np.abs(T - q).argmin() for q in targets]
        try:
            print(filename)
            print(T)
            print(indices)
            print(r1/41)
            if "#47C0B0" not in cor:
                ax.scatter(T[indices], r1[indices]/41, edgecolors=cor, facecolors='none', marker='o', s=10, label=f'{filename}')
                # ax.scatter(T[indices2], r1[indices2]/41, edgecolors=cor, facecolors='none', marker='o', s=10)
            else:
                print('hola')
                # ax.scatter(T[indices], r1[indices]/41, edgecolors=cor, facecolors='none', marker='o', s=10, label=f'$\delta$ > 0 {filename}')
                # ax.scatter(T[indices2], r1[indices2]/41, edgecolors=cor, facecolors='none', marker='o', s=10)
        except Exception as e:
            print(e)
            continue
    
    #dividir por 41 la r  
# rampas = get_files_with_path(dirs[1])
# for filename in rampas:
#     try:
#         T, s, h, v1, i1, r1, v2, i2, r2 = np.genfromtxt(filename, usecols=(1,2,3,4,5,6,7,8,9), delimiter=',', unpack=True, skip_header=1)
#         # Plot for i1 == 0.001
#         mask_1mA = np.isclose(i1, 0.001)
#         if np.any(mask_1mA):
#             T_1mA, r1_1mA = T[mask_1mA], r1[mask_1mA]
#             base_name = filename.split("rampas\\Rampa")[-1].split('.')[0]
#             # ax.scatter(T_1mA[40:-1], r1_1mA[40:-1], c="#4AF19D", s=10, label=f'{base_name} (I=1mA)')
#         # Plot for i1 == 0.0001
#         mask_0_1mA = np.isclose(i1, 0.0001)
#         if np.any(mask_0_1mA):
#             T_0_1mA, r1_0_1mA = T[mask_0_1mA], r1[mask_0_1mA]
#             base_name = filename.split("rampas\\Rampa")[-1].split('.')[0]
#             # ax.scatter(T_0_1mA, r1_0_1mA, c="#F14AE9", s=10, label=f'{base_name} (I=0,1mA)')
#     except Exception as e:
#         print(e)
#         continue
    #dividir por 0.36 la r  
xdeox = np.array([1, 10, 40, 50, 60, 70, 80, 90, 100, 105, 110, 120, 135, 150, 200, 250, 300])
ydeox = np.array([4e-2, 3.8e-2, 3.8e-2, 4e-2, 4.2e-2, 6e-2, 1e-1, 1.3e-1, 1.47e-1, 1.5e-1, 1.47e-1, 1.41e-1, 1.2e-1, 1.1e-1, 9e-2, 8e-2, 7.5e-2])
# mk = next(marker)
mk='o'
ax.plot(xdeox, ydeox, marker=None, ls='--', label='Qi et al. $\\rho_c$ ($\delta$ ~ 0.04)', color='black')
xdeox = np.array([1, 10, 40, 50, 60, 70, 100, 130, 160, 200, 250, 300])
ydeox = np.array([1e-5, 2e-5, 1e-3, 2e-3, 3e-3, 4e-3, 2e-2, 3e-2, 2.6e-2, 1.6e-2, 1e-2, 0.8e-2])
# mk = next(marker)
ax.plot(xdeox, ydeox, marker=None, ls='--', label='Qi et al. $\\rho_a$ ($\delta$ ~ 0.04)', color='blue')
ax.set_yscale('symlog')
# ax2.set_yscale('symlog')
ticks = np.array([0e-2, 2e-2, 4e-2, 6e-2, 8e-2, 1e-1, 1.2e-1, 1.4e-1, 1.6e-1, 1.8e-1, 2e-1, 2.2e-1, 2.4e-1, 2.6e-1])
ax.set_yticks([0e-2, 2e-2, 4e-2, 6e-2, 8e-2, 1e-1, 1.2e-1, 1.4e-1, 1.6e-1, 1.8e-1, 2e-1, 2.2e-1, 2.4e-1, 2.6e-1])
# ax2.set_yticks([0,1,2,3,4,5,6,7,8])
ax.set_ylim(-0.01,0.21)
# ax2.set_ylim(-0.4,8.4)
# ax2.set_ylabel('$R$ ($\Omega$)')
ax.set_xlabel('$T$ (K)')
ax.set_ylabel('$\\rho$ ($\Omega$ cm)')
# ax.set_xlim(8, 100)
# ax2.set_ylabel('R ($\Omega$)')
# plt.suptitle(f'Resistividad 4 terminales, I = 1 mA')
ax.set_xlabel('$T$ (K)')
# ax.set_ylabel('Resistencia ($\Omega$)')
# ax.set_yscale('log')
ax.legend(fontsize='large', frameon=False)
# ax.grid()
def format_func(value, tick_number):
    # Only format non-zero values (symlog has a linear region around 0)
    if value == 0:
        return "0"
        
    # Get the exponent and mantissa
    exponent = int(np.floor(np.log10(abs(value))))
    mantissa = value / (10**exponent)
    
    # Round mantissa to avoid floating point ugliness (e.g. 1.99999)
    mantissa = round(mantissa, 1)
    
    # If mantissa is an integer (e.g., 2.0), display as int (2)
    if mantissa.is_integer():
        mantissa_str = f"{int(mantissa)}"
    else:
        mantissa_str = f"{mantissa}"

    # Return the format: "mantissa space 10^{exponent}"
    # We use LaTeX formatting for the superscript
    return r"${0}\ 10^{{{1}}}$".format(mantissa_str, exponent)
ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_func))
data = np.genfromtxt('e:/trabajo/tesis 3/tesisfisica/squid/SIO1/MdeT_1000G_FC.rso.dat', skip_header=32, delimiter=',', unpack=True)
# Create the plot
plt.figure(figsize=(4, 3), dpi=450)
plt.plot(data[3][:-100], data[4][:-100], c="#47C0B0", lw=2)

plt.xlabel('T (K)')
plt.ylabel('M (emu)')

# Show the plot
# plt.vlines(100,0,0.000178, linestyles='--', label='$T_M=100 $ K', color='k')
# plt.vlines(240,-0.000043,0, linestyles='-.', label='$T_N=240 $ K', color='k')
# plt.ylim(-0.00005, 0.00020)
plt.legend(fontsize='large', frameon=False)
# plt.grid()
plt.show()
# %%
