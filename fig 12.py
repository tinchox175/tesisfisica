#%%
# -*- coding: utf-8 -*-
"""
Adapted Duffing Oscillator Panel Script (English, No Grid, Clean Labels)
"""
import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt
import matplotlib as mpl
from figure_editor import save_figure_data, load_figure, edit_cosmetics

# Adjusting global parameters for a multi-panel figure
mpl.rcParams.update({
    'font.size': 12,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10
})

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

def plot_time_series(ax, t, sol, title='', show_ylabel=True):
    """
    Plots x(t) on the provided axis (ax).
    """
    x = sol[:, 0]

    # Updated color to #6699e0 as requested
    ax.plot(t, x, label='x(t)', c='#6699e0', lw=2.5)
    ax.set_xlabel('Time (a.u.)')
    
    if show_ylabel:
        ax.set_ylabel('Amplitude (a.u.)')
        
    ax.set_title(title)
    ax.legend(frameon=False, loc='upper right')
    ax.grid(False) # Removed grid

def plot_phase_space(ax, t, sol, title='', show_ylabel=True):
    """
    Plots the phase space diagram on the provided axis (ax).
    """
    x = sol[:, 0][:-13000]
    v = sol[:, 1][:-13000]
    t = t[:-13000]
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

def main():
    # Initialize the 2x3 grid
    fig, axs = plt.subplots(2, 3, figsize=(16, 8), dpi=150)
    
    # Fixed parameters
    gamma = 0.1
    alpha = -1.0
    beta = 0.25
    
    # --- 1) TOP ROW: Variation in F_dc ---
    F_ac1 = 0.2
    omega_fixed = 1.0
    dc_values = [0.0, -0.5, -2.0] 
    
    for i, fdc in enumerate(dc_values):
        t, sol = simulate_duffing_dc(gamma=gamma, alpha=alpha, beta=beta,
                                     F_ac=F_ac1, omega=omega_fixed, F_dc=fdc,
                                     x0=0.1, v0=0.0,
                                     tmax=200, dt=0.01)
        title = f'$F_{{ac}}$={F_ac1}, $F_{{dc}}$={fdc}, $\\omega$={omega_fixed}'
        # Route the plot to the top row, only show Y label for the first column
        plot_time_series(axs[0, i], t, sol, title=title, show_ylabel=(i == 0))

    # --- 2) BOTTOM ROW: Variation in omega ---
    F_dc_chosen = 0.1
    F_ac2 = 0.5
    omegas = [2, 4, 16]
    
    for i, w in enumerate(omegas):
        t, sol = simulate_duffing_dc(gamma=gamma, alpha=alpha, beta=beta,
                                     F_ac=F_ac2, omega=w, F_dc=F_dc_chosen,
                                     x0=0, v0=0.0,
                                     tmax=200, dt=0.01)
        title = f'$F_{{ac}}$={F_ac2}, $F_{{dc}}$={F_dc_chosen}, $\\omega$={w}'
        # Route the plot to the bottom row, only show Y label for the first column
        plot_phase_space(axs[1, i], t, sol, title=title, show_ylabel=(i == 0))

    # Adjust layout and save
    plt.tight_layout()
    plt.savefig('Fig 12.pdf', format='pdf', bbox_inches='tight')
    plt.show()
    save_figure_data(fig, filename="Fig 12")

if __name__ == '__main__':
    main()