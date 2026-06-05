#%%
import matplotlib.pyplot as plt
import numpy as np
import os
import matplotlib as mpl
import matplotlib.ticker as ticker
from figure_editor import save_figure_data, load_figure, edit_cosmetics

# Global formatting
mpl.rcParams.update({
    'font.size': 5.5,
    'axes.titlesize': 16,
    'axes.labelsize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 10
})

def get_files_with_path(folder):
    return [os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]

def list_folders_in_folder(folder_path):
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]

# =========================================================================
# HELPER 1: MAGNETIZATION PLOT LOGIC
# =========================================================================
def plot_magnetization(ax):
    data = np.genfromtxt('E:/trabajo/tesis 3/tesisfisica/squid/SIO1/MdeT_1000G_FC.rso.dat', skip_header=32, delimiter=',', unpack=True)

    # Constants for Sr2IrO4 (n=1 phase)
    M_w = 431.46           # Molar mass in g/mol
    n_ir = 1               # Number of Ir atoms per formula unit
    conversion_factor = 5585
    sample_mass_g = 0.0006  # Keep an eye on this (0.6 mg vs 5 mg)

    data_M = (data[4][:-100] * M_w) / (sample_mass_g * n_ir * conversion_factor)

    ax.plot(data[3][:-100], data_M, c="#47C0B0", lw=2, label='M(T)')
    ax.set_xlabel('$T$ (K)')
    ax.set_ylabel('$M$ ($\\mu_B$/Ir)')

    # Optional bounds and lines
    ax.vlines(100, 0, 0.023, linestyles='--', label='$T_M\sim 100 $ K', color='k')
    ax.vlines(240, -0.0055, 0, linestyles='-.', label='$T_N\sim 240 $ K', color='k')
    ax.hlines(0,300,0, color='gray', lw=0.5)

    ax.legend(fontsize='large', frameon=False)

# =========================================================================
# HELPER 2: RESISTIVITY PLOT LOGIC
# =========================================================================
def plot_resistivity(ax):
    rampas = [
        'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT1212 I=10 mA.csv',
        'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT1212.csv',
        'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT1712b.csv',
        'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT1812.csv',
        'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT711.csv',
        'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT1312 I=0,1 mA.csv',
        'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT811.csv'
    ]

    for filename in rampas:
        try:
            T, s, h, v1, i1, r1, v2, i2, r2 = np.genfromtxt(filename, usecols=(1,2,3,4,5,6,7,8,9), delimiter=',', unpack=True, skip_header=1)
        except:
            t, T, s, h, r1, r2 = np.genfromtxt(filename, delimiter=',', unpack=True, skip_header=1)
        
        if filename == 'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT711.csv':
            continue
            r1 = r1[:]
            filename = 'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT7-11.csv'
            cor = "#F14A74"
            continue
        elif filename == 'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT1212 I=10 mA.csv':
            continue
            filename = 'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT1212 I=10.0$ mA'
            rc = r1[:400]
            Tc = T[:400]
            rc2 = r1[1900:]
            Tc2 = T[1900:]
            r1 = np.concatenate((rc, rc2))
            T = np.concatenate((Tc, Tc2))
            cor = "#E639AC"
        elif filename == 'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT811.csv':
            r1 = r1[:1571]
            T = T[:1571]
            filename = 'X5-a'
            cor = "#47C0B0"
            r1 = np.concatenate((r1[:672], r1[672:772]*0.92, r1[772:-1]*0.9))
        elif filename == 'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT1212.csv':
            continue
            r1 = r1[:1850]
            T = T[:1850]
            filename = 'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas/RampaRdeT1212 (I=1 mA).csv'
            cor = "#4AD0F1"
        elif filename == 'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT1312 I=0,1 mA.csv':
            continue
            filename = 'X1b $I=0.1$ mA'
            r1 = r1[:]
            T = T[:]
            window = 27 
            if window % 2 == 0:
                window += 1
            if r1.size >= window:
                kernel = np.ones(window) / window
                r1 = np.convolve(r1, kernel, mode='same')[15:-10]
            cor = "#F1A34A"
            T = T[15:-10]
            r1 = np.flip(r1)
            T = np.flip(T)
        elif filename == 'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT1712b.csv':
            filename = 'X5-b'
            cor = '#E63946'
        elif filename == 'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT1812.csv':
            continue
            filename = 'E:/trabajo/tesis 3/tesisfisica/criostato/Archivos/X5/rampas\\RampaRdeT18-12.csv'
            cor = "#4883F1"
            continue
            
        if '#47C0B0' in cor and '10' not in filename:
            targets = np.arange(0,300,6)
            indices = [np.abs(T - q).argmin() for q in targets]
            try:
                if "#47C0B0" not in cor:
                    ax.scatter(T[indices], r1[indices]/41, edgecolors=cor, facecolors='none', marker='o', s=10, label=f'{filename}')
                else:
                    ax.scatter(T[indices], r1[indices]/41, edgecolors=cor, facecolors='none', marker='o', s=10, label=f'{filename}')
            except Exception as e:
                print(e)
                continue
                
        if '10' not in filename and '#47C0B0' not in cor:
            targets1 = np.arange(100,300,7)
            targets2 = np.arange(45,100,6)
            targets = np.concatenate((targets1, targets2))
            indices = [np.abs(T - q).argmin() for q in targets]
            indices2 = [np.abs(r1/41 - q).argmin() for q in np.arange(0.09, 0.2, 0.005)]
            try:
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
                if "#47C0B0" not in cor:
                    ax.scatter(T[indices], r1[indices]/41, edgecolors=cor, facecolors='none', marker='o', s=10, label=f'{filename}')
                else:
                    pass
            except Exception as e:
                print(e)
                continue

    # Literature Data
    xdeox = np.array([1, 10, 40, 50, 60, 70, 80, 90, 100, 105, 110, 120, 135, 150, 200, 250, 300])
    ydeox = np.array([4e-2, 3.8e-2, 3.8e-2, 4e-2, 4.2e-2, 6e-2, 1e-1, 1.3e-1, 1.47e-1, 1.5e-1, 1.47e-1, 1.41e-1, 1.2e-1, 1.1e-1, 9e-2, 8e-2, 7.5e-2])
    ax.plot(xdeox, ydeox, marker=None, ls='--', label='Qi et al. $\\rho_c$ ($\delta$ ~ 0.04)', color='black')

    xdeox = np.array([1, 10, 40, 50, 60, 70, 100, 130, 160, 200, 250, 300])
    ydeox = np.array([1e-5, 2e-5, 1e-3, 2e-3, 3e-3, 4e-3, 2e-2, 3e-2, 2.6e-2, 1.6e-2, 1e-2, 0.8e-2])
    ax.plot(xdeox, ydeox, marker=None, ls='--', label='Qi et al. $\\rho_a$ ($\delta$ ~ 0.04)', color='blue')

    # Formatting for Resistivity
    ax.set_yscale('symlog')
    ax.set_yticks([0e-2, 2e-2, 4e-2, 6e-2, 8e-2, 1e-1, 1.2e-1, 1.4e-1, 1.6e-1, 1.8e-1, 2e-1, 2.2e-1, 2.4e-1, 2.6e-1])
    ax.set_ylim(-0.01, 0.21)
    ax.set_xlabel('$T$ (K)')
    ax.set_ylabel('$\\rho$ ($\Omega$ cm)')

    # Handle legend reordering specifically for this ax
    handles, labels = ax.get_legend_handles_labels()
    try:
        order = [1, 0, 3, 2]
        ax.legend([handles[idx] for idx in order], [labels[idx] for idx in order], fontsize='large', frameon=False)
    except IndexError:
        ax.legend(handles, labels, fontsize='large', frameon=False)

    def format_func(value, tick_number):
        if value == 0: return "0"
        exponent = int(np.floor(np.log10(abs(value))))
        mantissa = value / (10**exponent)
        mantissa = round(mantissa, 1)
        mantissa_str = f"{int(mantissa)}" if mantissa.is_integer() else f"{mantissa}"
        return r"${0}\ 10^{{{1}}}$".format(mantissa_str, exponent)

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_func))

# =========================================================================
# FIGURE EXPORTING BLOCK
# =========================================================================

# 1. OPTION A: Magnetization Only
fig_mag, ax_mag_only = plt.subplots(figsize=(4, 3), dpi=450)
plot_magnetization(ax_mag_only)
fig_mag.tight_layout()
fig_mag.savefig('Fig 2a.pdf', format='pdf')
save_figure_data(fig_mag, filename="Fig 2a")

# 2. OPTION B: Resistivity Only
fig_res, ax_res_only = plt.subplots(figsize=(4, 3), dpi=450)
plot_resistivity(ax_res_only)
fig_res.tight_layout()
fig_res.savefig('Fig 2b.pdf', format='pdf')
save_figure_data(fig_res, filename="Fig 2b")

# 3. OPTION C: Combined 1x2 Panel
fig_both, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(8, 3), dpi=450)
plot_magnetization(ax_left)
plot_resistivity(ax_right)
fig_both.tight_layout()
fig_both.savefig('Fig 2.pdf', format='pdf')
save_figure_data(fig_both, filename="Fig 2")

plt.show()
#%%