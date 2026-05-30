#%%
import numpy as np
import matplotlib.pyplot as plt
import os
from matplotlib.colors import LinearSegmentedColormap
from figure_editor import save_figure_data, load_figure, edit_cosmetics

os.chdir('C:/LBT/tesisfisica')

# Custom colormap
cmap = LinearSegmentedColormap.from_list("custom_blue", ["#c4d2e7", "#1661ec"])

# Files to process
files = [
    '/criostato/Archivos/iv/1312/iv-x5-f2-15K-2nplc.csv',
    '/criostato/Archivos/iv/1312/iv-x5-w1-14K-2nplc.csv'
]

# Initialize 2x2 Grid (sharex='col' shares the V-axis between top and bottom plots)
fig, axs = plt.subplots(2, 2, figsize=(7, 5), dpi=150, sharex='col')

for n, archivo_actual in enumerate(files):
    
    # 1. Parse the specific nplc file format
    # Using unpack=True means data[0] is time, data[1] is V, data[2] is I, etc.
    data = np.genfromtxt(os.getcwd()+archivo_actual, delimiter=',', skip_header=1, unpack=True)
    
    # Clean NaNs
    mask = ~np.isnan(data[0])
    time = data[0][mask]
    vin1 = np.array(data[1][mask])
    iin1 = data[2][mask] * 1000      # I instant in mA
    # vbi1 = data[3][mask]           # V bias (unused in plot)
    # ibi1 = data[4][mask] * 1000    # I bias (unused in plot)
    
    temperatura = archivo_actual.split('-')[-2]
    filename_clean = archivo_actual.split('/')[-1]

    # 2. Calculate Gamma
    # Suppress divide-by-zero warnings common when calculating log(abs(0))
    with np.errstate(divide='ignore', invalid='ignore'):
        gam1 = np.diff(np.log(np.abs(iin1))) / np.diff(np.log(np.abs(vin1)))
    
    # 3. Route to the correct column in the 2x2 grid
    if n == 0:
        ax_iv = axs[0, 0]  # Top Left
        ax_g = axs[1, 0]   # Bottom Left
    elif n == 1:
        ax_iv = axs[0, 1]  # Top Right
        ax_g = axs[1, 1]   # Bottom Right
    else:
        break # Failsafe just in case you add more than 2 files to the list
        
    # 4. Plot IV Curve (Top Row)
    ax_iv.scatter(vin1, iin1, s=15, c=time, cmap=cmap)
    # ax_iv.set_title(f"{filename_clean} ({temperatura})")
    if n == 0:
        ax_iv.set_ylabel('I (mA)')
        ax_iv.set_yticks([0, 5, 10, 15, 20])
    else:
        
        ax_iv.set_yticks([0, 5, 10, 15])
    # ax_iv.grid(True)
    
    # 5. Plot Gamma (Bottom Row)
    # Array sizes: gam1 is 1 element shorter due to diff, so we slice vin1[:-1] and time[:-1]
    ax_g.scatter(vin1[:-1], gam1, s=15, c=time[:-1], cmap=cmap)
    ax_g.set_xlabel('V (V)')
    if n == 0:
        ax_g.set_ylabel('$\gamma$')
    
    # Optional: Gamma plots often have wild spikes near V=0. 
    # You may want to un-comment and tweak this y-limit to zoom in on the SCLC transitions.
    # ax_g.set_ylim(-2, 10) 
    # ax_g.grid(True)

plt.tight_layout()
plt.savefig('Fig 5.pdf', format='pdf')
plt.show()
save_figure_data(fig, filename="Fig 5")
#%%