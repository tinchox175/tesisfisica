#%%
import numpy as np
import matplotlib.pyplot as plt
import os
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from figure_editor import save_figure_data, load_figure, edit_cosmetics

os.chdir('C:/LBT/tesisfisica')

# Custom colormap
cmap = LinearSegmentedColormap.from_list("custom_blue", ["#b3d1ff", "#4c86f0"])

# The 6 files for the 3x2 grid
files = [
    '/criostato/Archivos/iv/1312/iv-x5-d-15K-2nplc.csv',
    '/criostato/Archivos/iv/1312/iv-x5-e-15K-2nplc.csv',
    '/criostato/Archivos/iv/1312/iv-x5-h-15K-0.2nplc.csv',
    '/criostato/Archivos/iv/1312/iv-x5-i-15K-0.2nplc.csv',
    '/criostato/Archivos/iv/1312/iv-x5-p-14K-1nplc.csv',
    '/criostato/Archivos/iv/1312/iv-x5-r1-14K-1nplc.csv'
]

# Initialize 3x2 Grid 
# sharex=True shares the V-axis across all columns so only the bottom row gets labels
fig, axs = plt.subplots(2, 3, figsize=(12, 6), dpi=150)


# Flatten the 3x2 array into a 1D list of 6 axes for easy iteration
axs = axs.flatten()

for n, archivo_actual in enumerate(files):
    
    # Failsafe: if you accidentally pass fewer/more than 6 files, this prevents a crash
    if n >= 6: 
        break
        
    ax = axs[n]
    
    # 1. Parse the specific nplc file format
    data = np.genfromtxt(os.getcwd()+archivo_actual, delimiter=',', skip_header=1, unpack=True)
    
    # Clean NaNs
    # mask = ~np.isnan(data[0])
    time = data[0]
    vin1 = np.array(data[1])
    
    # Current for calculating Ohms (A)
    I_A = data[2]            
    
    temperatura = archivo_actual.split('-')[-2]
    filename_clean = archivo_actual.split('/')[-1]

    # 2. Calculate Resistances (in Ohms)
    with np.errstate(divide='ignore', invalid='ignore'):
        # Instantaneous: V / I
        r_inst = (vin1 / I_A)
        # Differential: dV / dI
        r_diff = (np.diff(vin1) / np.diff(I_A))
    
    # 3. Plot Resistances
    # Instantaneous Resistance in Gray (zorder=1 pushes it behind)
    ax.plot(vin1, r_inst, lw=3, c='gray', alpha=1, zorder=10)
    
    # Differential Resistance in Color (mapped to time, zorder=2 pulls it forward)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("custom_blue", ["#b3d1ff", "#4c86f0"])
    ax.scatter(vin1[:-1], r_diff, c=time[:-1], cmap=cmap, zorder=2)
    
    # 4. Formatting
    # ax.set_title(f"{filename_clean} ({temperatura})", fontsize=10)
    # ax.set_yscale('log') 
    # ax.grid(True)
    
    # Only put Y-labels on the left column (indices 0, 2, 4)
    # if n % 2 == 0:
    ax.set_ylabel('$R$ ($\Omega$)')
        
    # Only put X-labels on the bottom row (indices 4, 5)
    if n >= 4:
        ax.set_xlabel('$V$ (V)')
        
    # Add a custom legend to the very first plot only
    if n == 0:
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#4c86f0', markersize=7, label='$R_{diff}$'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=7, label='$R_{inst}$')
        ]
        # ax.legend(handles=legend_elements, loc='best', frameon=False)

plt.tight_layout()
plt.savefig('Fig 6.pdf', format='pdf')  # Save the figure as a high-res PNG
plt.show()
save_figure_data(fig, filename="Fig 6") #el nombre que elegimos para su archivo
#%%