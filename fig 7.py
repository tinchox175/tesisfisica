#%%
import numpy as np
import matplotlib.pyplot as plt
import os
import matplotlib as mpl
from natsort import natsorted
import itertools
from figure_editor import save_figure_data, load_figure, edit_cosmetics
from matplotlib.colors import LinearSegmentedColormap

# Apply your styling
mpl.rcParams.update({
    'font.size': 14,
    'axes.titlesize': 16,
    'axes.labelsize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 10
})
cmap = LinearSegmentedColormap.from_list("custom_blue", ["#b3d1ff", "#4c86f0"])

marker_l = lambda : itertools.cycle(('.', 'o', 'v', '^', '<', '>', '1', '2', '3', '4', '8', 's', 'p', '*', 'h', 'H', '+', 'x', 'D', 'd', '|', 'P', 'X'))

def get_files_with_path(folder):
    return [os.path.join(folder, file) for file in natsorted(os.listdir(folder)) if os.path.isfile(os.path.join(folder, file))]

def list_folders_in_folder(folder_path):
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]

# Base Directories
dir_16 = "E:/trabajo/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
dir_18 = "E:/trabajo/tesis 3/tesisfisica/IVs/1812/ZdeW_1234_18-12-24/"

# 1. Initialize the 2x2 grid
fig, axs = plt.subplots(2, 2, figsize=(12, 6), dpi=200, sharex=True)

ax_zimag_16 = axs[0, 0]  # Top Left: 16-11 Z''
ax_zimag_18 = axs[0, 1]  # Top Right: 18-12 Z''
ax_zreal_16 = axs[1, 0]  # Bottom Left: 16-11 Z'
ax_zreal_18 = axs[1, 1]  # Bottom Right: 18-12 Z'
target_temp1 = '291.02'
target_temp2 = '280.79'

# 2. Helper function to plot a directory's data onto specific axes
def plot_impedance_data(base_dir, ax_zimag, ax_zreal, title):
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
    
    # Reset marker cycle so legends match perfectly between dates
    marker = marker_l() 
    
    # Generate a gradient palette based on the number of files
    # You can change 'viridis' to 'plasma', 'inferno', 'magma', or 'coolwarm'
    cmap = plt.get_cmap('coolwarm')
    colors = cmap(np.linspace(0, 1, len(files)))
    
    for idx, i in enumerate(files):
        off = (i.split('_')[-2]).split('.')[0]
        data = np.genfromtxt(i, unpack=True, delimiter=',')
        
        freq = data[0]
        z_real = data[1] # Z'
        z_imag = data[3] # Z''
        
        mk = next(marker)
        c = colors[idx]  # Grab the specific color from the gradient for this file
        
        # Plot Z'' on top, Z' on bottom with the new color argument
        ax_zimag.plot(freq, z_imag, color=c, markerfacecolor='none', label=str(off) + ' mV', lw=1)
        ax_zreal.plot(freq, z_real, color=c, markerfacecolor='none', label=str(off) + ' mV', lw=1)
        
    # ax_zimag.set_title(title)

# 3. Plot both sets of data
plot_impedance_data(dir_16, ax_zimag_16, ax_zreal_16, "16-11")
plot_impedance_data(dir_18, ax_zimag_18, ax_zreal_18, "18-12")

# 4. Global Formatting
ax_zimag_16.set_ylabel("$Z''$ ($\Omega$)")
ax_zreal_16.set_ylabel("$Z'$ ($\Omega$)")

ax_zreal_16.set_xlabel("$f$ (Hz)")
ax_zreal_18.set_xlabel("$f$ (Hz)")

# Log scale for frequency
ax_zreal_16.set_xscale('log')
ax_zreal_18.set_xscale('log')

# for ax in axs.flatten():
    # ax.grid(True, alpha=0.5)

# 5. Global Legend on the Far Right
# Try to grab labels from the left plot first
handles, labels = ax_zimag_16.get_legend_handles_labels()

# If the left plot is empty, grab them from the right plot instead
if not handles:
    handles, labels = ax_zimag_18.get_legend_handles_labels()

if handles:
    # Shrink the main plots slightly to make room for the legend on the right
    plt.subplots_adjust(right=0.82)
    # Place legend outside the axes
    fig.legend(handles, labels, loc='center left', bbox_to_anchor=(0.83, 0.5), frameon=False)
else:
    plt.tight_layout()

# plt.savefig('Impedance_Comparison_291K.png', bbox_inches='tight')
plt.savefig('Fig 7.pdf', format='pdf')
plt.show()
save_figure_data(fig, filename="Fig 7")  # Save the figure data for future editing