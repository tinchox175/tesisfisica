#%%
# -*- coding: utf-8 -*-
"""
Adapted Duffing Oscillator Panel Script (English, No Grid, Clean Labels)
"""
import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt
import os
import matplotlib as mpl
from natsort import natsorted
from figure_editor import save_figure_data, load_figure, edit_cosmetics
from matplotlib.colors import LinearSegmentedColormap

# Adjusting global parameters for a multi-panel figure
mpl.rcParams.update({
    'font.size': 12,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10
})

def get_files_with_path(folder):
    return [os.path.join(folder, file) for file in natsorted(os.listdir(folder)) if os.path.isfile(os.path.join(folder, file))]

def list_folders_in_folder(folder_path):
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]

# Base Directories
dir_16 = "E:/trabajo/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
dir_18 = "E:/trabajo/tesis 3/tesisfisica/IVs/1812/ZdeW_1234_18-12-24/"
def duffing_equations_dc(y, t, gamma, alpha, beta, F_ac, omega, F_dc):
    """
    y[0] = x(t)
    y[1] = v(t) = dx/dt
    
    Duffing equations with AC (F_ac*cos(omega*t)) and DC (F_dc) forcing.
    """
    x, v = y
    dxdt = v
    dvdt = -gamma*v - alpha*x - beta*x**3 + F_ac*np.cos(omega*t) + F_dc
    return [dxdt, dvdt]

def simulate_duffing_dc(gamma=0.1, alpha=-1.0, beta=1.0,
                        F_ac=0.0, omega=1.0, F_dc=0.0,
                        x0=-0.5, v0=0.0,
                        tmax=200, dt=0.01):
    """
    Integrates the Duffing equation.
    Returns the time vector and the solution (x(t), v(t)).
    """
    t = np.arange(0, tmax, dt)
    y0 = [x0, v0]
    sol = odeint(duffing_equations_dc, y0, t,
                 args=(gamma, alpha, beta, F_ac, omega, F_dc))
    
    return t, sol

def plot_phase_space(ax, t, sol, title='', show_ylabel=True):
    """
    Plots the phase space diagram on the provided axis (ax).
    """
    x = sol[:, 0]
    v = sol[:, 1]
    t = t
    # Normalize t for colormap
    t_norm = (t - np.min(t)) / (np.max(t) - np.min(t))
    t_norm = t_norm ** 0.4
    
    cmap = mpl.colors.LinearSegmentedColormap.from_list(
        'pastel_blue_black',
        ['#dceeff', "#b9d6ff", "#74acf1", "#3a6eb6", '#000000']
    )
    
    ax.scatter(x, v, c=t_norm, cmap=cmap, s=2)
    ax.set_xlabel('x (a.u.)')
    
    if show_ylabel:
        ax.set_ylabel('v = dx/dt (a.u.)')
        
    ax.set_title(title)
    ax.grid(False) # Removed grid

target_temp1 = '140'
target_temp2 = '90.17'

def plot_impedance_data(base_dir, ax_zreal, title):
    folders = list_folders_in_folder(base_dir)
    target_folder = None
    
    # Find the specific temperature folder
    for f in folders:
        if target_temp1 in f or target_temp2 in f:
            target_folder = os.path.join(base_dir, f)
            break
            
    if not target_folder:
        print(f"Warning: No folder with {target_temp1} or {target_temp2} found in {base_dir}")
        return
        
    files = get_files_with_path(target_folder)
    
    # Generate a gradient palette based on the number of files
    # You can change 'viridis' to 'plasma', 'inferno', 'magma', or 'coolwarm'
    cmap = plt.get_cmap('coolwarm')
    colors = cmap(np.linspace(0, 1, len(files)))
    
    for idx, i in enumerate(files):
        off = (i.split('_')[-2]).split('.')[0]
        if off == '0' or off == '20':
            pass
        else:
            continue
        data = np.genfromtxt(i, unpack=True, delimiter=',', skip_header=2)
        
        freq = data[0]
        z_real = data[1] # Z'
        z_imag = data[3] # Z''
        
        c = colors[idx]  # Grab the specific color from the gradient for this file
        
        # Plot Z'' on top, Z' on bottom with the new color argument
        ax_zreal.plot(freq, z_real, color=c, marker='o', label=str(off) + ' mV', lw=1)
        ax_zreal.set_title(target_temp1 + ' K' if target_temp1 in target_folder else target_temp2 + ' K')
    # ax_zimag.set_title(title)
def main():
    # Initialize the 2x3 grid
    fig, axs = plt.subplots(1,2, figsize=(8, 3), dpi=150)
    
    # Fixed parameters
    gamma = 0.1
    alpha = -1.0
    beta = 0.25
    
    F_dc_chosen = 0.1
    F_ac2 = 0.5
    w = 1
    
    t, sol = simulate_duffing_dc(gamma=gamma, alpha=alpha, beta=beta,
                                    F_ac=F_ac2, omega=w, F_dc=F_dc_chosen,
                                    x0=0, v0=0.0,
                                    tmax=200, dt=0.01)
    title = f'$F_{{ac}}$={F_ac2}, $F_{{dc}}$={F_dc_chosen}, $\\omega$={w}'
    # Route the plot to the bottom row, only show Y label for the first column
    plot_phase_space(axs[0], t, sol, title=title)
    plot_impedance_data(dir_16, axs[1], "16-11")
    axs[1].set_xscale('log')
    axs[1].set_xlabel('$f$ (Hz)')
    axs[1].set_ylabel("$Z'$ ($\Omega$)")
    axs[1].legend(frameon=False)
    # Adjust layout and save
    plt.tight_layout()
    plt.savefig('Fig 13.pdf', format='pdf', bbox_inches='tight')
    plt.show()
    save_figure_data(fig, filename="Fig 13")

if __name__ == '__main__':
    main()