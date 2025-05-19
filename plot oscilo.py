#%%
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import os
import concurrent.futures
import time
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit
from matplotlib.animation import FuncAnimation
import matplotlib.cm as cm
import matplotlib.colors as mcolors
%matplotlib qt
#%%
def lin(V, R, c):
    return V/R+c
def get_indices_above_threshold(values, threshold):
    """Returns indices of values above the threshold."""
    return np.where(values > threshold)[0]

def filter_arrays_by_indices(arrays, indices):
    """Filters multiple arrays using the given indices."""
    return [arr[indices] for arr in arrays]
def get_files_in_folder(folder_path):
    # Get all files in the folder
    return [file for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file))]
#%%
matplotlib.use('QtAgg')
alpha_decay = 0.92
line_width_decay = 0.92
initial_linewidth = 2.5  # width of newest segment
der = 'e:/porno/tesis 3/tesisfisica/IVs/2611/B/'
t_skip = -10
fig, ax = plt.subplots(1,2, figsize=(10, 6))
# axr = ax[0].twinx()
# axp = ax[1].twiny()
j = 'tek0008ALL.csv'
data = np.genfromtxt(der+j, unpack=True, delimiter=',', skip_header=20, skip_footer=0)
threshold = -10
indices = get_indices_above_threshold(data[1], threshold)
ws = 100
p = 3
x, y, z, w, v = filter_arrays_by_indices([data[0], savgol_filter(data[1], ws, p), savgol_filter(data[2], ws, p), savgol_filter(data[3], ws, p), savgol_filter(data[4], ws, p)], indices)
y = y
z = z
cmap = cm.plasma  # You can also try 'viridis', 'inferno', 'magma', 'cividis', etc.
norm = mcolors.Normalize(vmin=0, vmax=len(x))
ax[0].plot(x, y, label='Canal 1')
try:
    ax[0].plot(x, z, label='Canal 2')
except:
    pass
try:
    ax[0].plot(x, w, label='Canal 3')
except:
    pass
try:
    ax[0].plot(x, v, label='Canal 4')
except:
    pass
#major_ticks = np.arange(-2, 10, 1)
#minor_ticks = np.arange(-2, 10, 0.5)
#ax.set_yticks(minor_ticks, minor=True)
ax[0].grid()
ax[0].set_ylabel('Amplitud (V)')
ax[0].set_xlabel('Tiempo (s)')
# axi = ax[0].twinx()
I = (y-z)/30
# ies = axi.plot(x, I, label='I', color='k')
# sc1 = ax[1].scatter(z-v, I, marker='o', c=x, cmap='hot', label='IV 2T', zorder=1)
# pel = axp.scatter(w-v, I, marker='o', c=w-v, cmap='cool', label='IV 4T', zorder=0)
# popt, pcov = curve_fit(lin, w-v, I, p0=[0.0001,0])
# aj = axp.plot(w-v, lin(w-v,*popt), color='black', zorder=10, label='Ajuste 4T')
ax[1].grid()
ax[1].set_ylim(np.min(I)*0.9, np.max(I)*1.1)
ax[1].set_xlim(np.min(w-v)*0.9, np.max(w-v)*1.1)
trail_x = []
trail_y = []
# Create one Line2D object for the trail
trail_line, = ax[1].plot([], [], color='magenta', lw=2)
current_point, = ax[0].plot([], [], 'o', color='magenta', markersize=8)
def animate(i):
    trail_x.append(w[i]-v[i])
    trail_y.append(I[i])
    current_point.set_data([x[i]], [y[i]])
    trail_line.set_data(trail_x, trail_y)
    trail_line.set_color(cmap(norm(i)))  # Change color over time
    trail_line.set_alpha(1.0)
    return current_point, trail_line 
ani = FuncAnimation(fig, animate, frames=len(w-v), interval=0.001, blit=True, repeat=False)
plt.show()
# ax[1].grid()
# ax[1].set_ylabel('Corriente (mA)')
# ax[1].set_xlabel('Voltaje 2t (V)')
# axp.set_xlabel('Voltaje 4t (V)')
# lines, labels = ax[1].get_legend_handles_labels()
# lines2, labels2 = axp.get_legend_handles_labels()
# plt.legend(lines + lines2, labels + labels2, framealpha=1.0)
# rx = (w-v)/I
# rxsg = savgol_filter(rx, ws, 3)
# re = axr.scatter(x[np.where(rx<4)], savgol_filter(rx, ws, 3)[np.where(rx<4)], s=1, color='k', label='$R_{inst}$', zorder=0)
# axr.set_ylabel('Resistencia (Ohm)')
# axr.set_ylim(-10,10)
# lines, labels = ax[0].get_legend_handles_labels()
# lines2, labels2 = axr.get_legend_handles_labels()
# axr.legend(lines + lines2, labels + labels2, framealpha=1.0)
# # cbar1 = plt.colorbar(sc1, ax=ax[1], label="Tiempo")
# # cbar2 = plt.colorbar(pel, ax=ax[1])
# # cbar2.ax.yaxis.set_ticks([])
# plt.colorbar(pel, ax=axp, label='Tiempo')
# plt.suptitle(f'ws={ws}, p={p}, {i} \n'+'$R_{ajuste}$'+f'={np.round(popt[0],3)}$\pm${np.round(np.sqrt(np.diag(pcov))[0],3)}')
# plt.tight_layout()
# plt.savefig(i+'.png')
# break
#%%
%matplotlib qt
der = 'e:/porno/tesis 3/tesisfisica/IVs/2611/B/'
t_skip = -10
for i in ['tek0033ALL.csv', 'tek0034ALL.csv', 'tek0035ALL.csv', 'tek0036ALL.csv', 'tek0037ALL.csv']:
    fig, ax = plt.subplots(1,2, figsize=(10, 6), layout='compressed')
    # axr = ax[0].twinx()
    # axp = ax[1].twiny()
    data = np.genfromtxt(der+i, unpack=True, delimiter=',', skip_header=20, skip_footer=0)
    threshold = -10
    indices = get_indices_above_threshold(data[1], threshold)
    ws = 100
    p = 3
    x, y, z, w, v = filter_arrays_by_indices([data[0], savgol_filter(data[1], ws, p), savgol_filter(data[2], ws, p), savgol_filter(data[3], ws, p), savgol_filter(data[4], ws, p)], indices)
    # x = data[0][::1]
    # y = data[1][::1]
    # try:
    #     z = data[2][::1]
    # except:
    #     pass
    # try:
    #     w = data[3][::1]
    # except:
    #     pass
    # try:
    #     v = data[4][::1]
    # except:
    #     pass
    y = y
    z = z
    ax[0].plot(x, y, label='Canal 1')
    try:
        ax[0].plot(x, z, label='Canal 2')
    except:
        pass
    try:
        ax[0].plot(x, w, label='Canal 3')
    except:
        pass
    try:
        ax[0].plot(x, v, label='Canal 4')
    except:
        pass
    #major_ticks = np.arange(-2, 10, 1)
    #minor_ticks = np.arange(-2, 10, 0.5)
    #ax.set_yticks(minor_ticks, minor=True)
    ax[0].grid()
    ax[0].set_ylabel('Amplitud (V)')
    ax[0].set_xlabel('Tiempo (s)')
    # axi = ax[0].twinx()
    I = (y-z)/30
    # ies = axi.plot(x, I, label='I', color='k')
    # sc1 = ax[1].scatter(z-v, I, marker='o', c=x, cmap='hot', label='IV 2T', zorder=1)
    pel = ax[1].scatter(w-v, I, marker='o', c=x, cmap='cool', label='IV 4T', zorder=0)
    popt, pcov = curve_fit(lin, w-v, I, p0=[0.0001,0])
    aj = ax[1].plot(w-v, lin(w-v,*popt), color='black', zorder=10, label='Ajuste 4T')
    ax[1].grid()
    ax[1].set_ylabel('Corriente (mA)')
    ax[1].set_xlabel('Voltaje (V)')
    lines, labels = ax[1].get_legend_handles_labels()
    # lines2, labels2 = axp.get_legend_handles_labels()
    plt.legend(lines , labels , framealpha=1.0)
    rx = (w-v)/I
    rxsg = savgol_filter(rx, ws, 3)
    # re = axr.scatter(x[np.where(rx<4)], savgol_filter(rx, ws, 3)[np.where(rx<4)], s=1, color='k', label='$R_{inst}$', zorder=0)
    # axr.set_ylabel('Resistencia (Ohm)')
    # axr.set_ylim(-10,10)
    lines, labels = ax[0].get_legend_handles_labels()
    # lines2, labels2 = axr.get_legend_handles_labels()
    ax[0].legend(lines , labels , framealpha=1.0)
    # cbar1 = plt.colorbar(sc1, ax=ax[1], label="Tiempo")
    # cbar2 = plt.colorbar(pel, ax=ax[1])
    # cbar2.ax.yaxis.set_ticks([])
    # plt.colorbar(pel, ax=ax[1], label='Tiempo')
    # plt.suptitle(f'ws={ws}, p={p}, {i} \n'+'$R_{ajuste}$'+f'={np.round(popt[0],3)}$\pm${np.round(np.sqrt(np.diag(pcov))[0],3)}')
    # plt.tight_layout()
    plt.savefig(i+'.png')
    # break

# %%
