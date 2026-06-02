#%%
import numpy as np
import matplotlib.pyplot as plt
import os
import matplotlib as mpl
from matplotlib.colors import Normalize, LinearSegmentedColormap
from scipy.interpolate import griddata
from mpl_toolkits.axes_grid1 import make_axes_locatable
from figure_editor import save_figure_data, load_figure, edit_cosmetics

# Global Paper Formatting
mpl.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10
})

def get_files_with_path(folder):
    return [os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]

def list_folders_in_folder(folder_path):
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]

# Custom Colormap
colors = [
    (0.0, "#000000"), (0.1, "#2c105c"), (0.15, "#3d28a0"), (0.2, "#4141a5"), 
    (0.25, "#0072ff"), (0.3, "#00a5ff"), (0.35, "#00d8ff"), (0.4, "#7dffba"), 
    (0.45, "#a8ffc7"), (0.5, "#d4ffd3"), (0.55, "#ffff5e"), (0.6, "#ffd700"), 
    (0.7, "#ffa600"), (0.8, "#ff3d00"), (0.9, "#ff9cfb"), (1.0, "#ffffff")
]
cemap = LinearSegmentedColormap.from_list("custom_cmap", list(colors))

# Base Directories
dir_16 = "E:/trabajo/tesis 3/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
dir_18 = "E:/trabajo/tesis 3/tesisfisica/IVs/1812/ZdeW_1234_18-12-24/"

# =========================================================================
# CONFIGURATION MATRIX
# =========================================================================
plot_config = {
    '16_temps': ['280.79', '160.35', '85.12'],
    '18_temps': ['291.02', '170.48', '90.17'],
    
    # Defaults: (vmin, vmax, contour_level)
    'Z_real_default': (-1, 10, 0),     # Contour at 0 for NDR shading
    'Z_imag_default': (-2, 2, -0.18),  # Your original Z'' contour
    
    # Quirks for the 18-12 Reactance (Temp: (vmin, vmax, contour))
    '18_Z_imag_quirks': {
        '280': (-10, 2, -0.18),
        '160': (-10, 2, -0.18),
        '85':  (-125, 10, -0.18)
    }
}

# =========================================================================
# HELPER FUNCTION: Processes data and draws the contour map
# =========================================================================
def plot_contour(ax, base_dir, target_temp, is_reactance, vmin, vmax, contour_lvl):
    folders = list_folders_in_folder(base_dir)
    target_folder = next((os.path.join(base_dir, f) for f in folders if target_temp in f), None)
    
    if not target_folder:
        ax.text(0.5, 0.5, f'Missing:\n{target_temp}K', ha='center', va='center')
        ax.set_axis_off()
        return None

    files = get_files_with_path(target_folder)
    files = [f for f in files if f.endswith('.txt')]
    
    X0, Y0, Z0 = [], [], []
    data_idx = 3 if is_reactance else 1 # data[3] for Z'', data[1] for Z'
    
    for f in files:
        data = np.genfromtxt(f, unpack=True, delimiter=',')
        X = data[0][1:]
        Z = data[data_idx][1:]
        Y = np.full_like(X, float((f.split('_')[-2]).split('.')[0]))
        X0 = np.append(X0, X)
        Y0 = np.append(Y0, Y)
        Z0 = np.append(Z0, Z)

    # Griddata Interpolation
    xi = np.linspace(np.min(X0), np.max(X0), 1000)
    yi = np.linspace(np.min(Y0), np.max(Y0), 300)
    Xi, Yi = np.meshgrid(xi, yi)
    Zi = griddata((X0, Y0), Z0, (Xi, Yi), method='linear')

    # Plotting
    norm = Normalize(vmin=vmin, vmax=vmax)
    # Add rasterized=True
    mesh = ax.pcolormesh(Xi, Yi, Zi, antialiased=True, shading='gouraud', cmap=cemap, norm=norm, rasterized=True)
    
    # Contours 
    lvl = -1 if not is_reactance else contour_lvl
    ax.contour(Xi, Yi, Zi, alpha=1, levels=[lvl], colors='Grey', linestyle='dashed', linewidths=2)
    
    # Add rasterized=True here too, since it is a filled polygon layer
    ax.contourf(Xi, Yi, Zi, alpha=0.5, levels=[-9999, lvl], cmap='Greys', antialiased=True, rasterized=True)
    
    # Guide Lines
    # ax.axvline(180, 0, 1, c='gray', ls='--', alpha=0.8)
    
    ax.set_xscale('log')
    ax.grid(True, alpha=0.3)
    
    return mesh

# =========================================================================
# FIGURE LAYOUT AND EXECUTION (3 Rows x 4 Columns)
# =========================================================================
fig, axs = plt.subplots(3, 4, figsize=(16, 10), dpi=250, sharex=True, sharey=True)

for row in range(3):
    temp_16 = plot_config['16_temps'][row]
    temp_18 = plot_config['18_temps'][row]
    
    # --- COL 0: Crystal a (16-11) Z' (Resistance) ---
    vmin, vmax, clvl = plot_config['Z_real_default']
    m0 = plot_contour(axs[row, 0], dir_16, temp_16, False, vmin, vmax, clvl)
    
    # --- COL 1: Crystal a (16-11) Z'' (Reactance) ---
    vmin, vmax, clvl = plot_config['Z_imag_default']
    m1 = plot_contour(axs[row, 1], dir_16, temp_16, True, vmin, vmax, clvl)
    
    # --- COL 2: Crystal b (18-12) Z' (Resistance) ---
    vmin, vmax, clvl = plot_config['Z_real_default']
    m2 = plot_contour(axs[row, 2], dir_18, temp_18, False, vmin, vmax, clvl)
    
    # --- COL 3: Crystal b (18-12) Z'' (Reactance) ---
    vmin, vmax, clvl = plot_config['18_Z_imag_quirks'].get(temp_18, plot_config['Z_imag_default'])
    m3 = plot_contour(axs[row, 3], dir_18, temp_18, True, vmin, vmax, clvl)

    # Attach specific Colorbars to the right side of each subplot
    for col, mesh in enumerate([m0, m1, m2, m3]):
        if mesh:
            divider = make_axes_locatable(axs[row, col])
            cax = divider.append_axes("right", size="5%", pad=0.05)
            cbar_label = "$Z''$ ($\Omega$)" if col in [1, 3] else "$Z'$ ($\Omega$)"
            plt.colorbar(mesh, cax=cax, label=cbar_label)

# =========================================================================
# FORMATTING & LABELS
# =========================================================================
# Left Column Y-Labels
axs[0, 0].set_ylabel("DC Bias (mV)")
axs[1, 0].set_ylabel("DC Bias (mV)")
axs[2, 0].set_ylabel("DC Bias (mV)")

# Bottom Row X-Labels (Frequency)
for col in range(4):
    axs[2, col].set_xlabel('f (Hz)')

plt.tight_layout()
plt.savefig('Fig 8.pdf', format='pdf', dpi=300)
plt.show()
save_figure_data(fig, filename="Fig 8")  # Save the figure data for future editing
#%%