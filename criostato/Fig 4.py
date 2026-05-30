import os
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker
import matplotlib.colors as mcolors
import itertools
from matplotlib.colors import LinearSegmentedColormap
import matplotlib as mpl
from figure_editor import save_figure_data, load_figure, edit_cosmetics

mpl.rcParams.update({
    'font.size': 5.5,
    'axes.titlesize': 16,
    'axes.labelsize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 10
})
%matplotlib inline
def get_files_in_folder(folder_path):
    # Get all files in the folder
    return [file for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file))]
folder_path = "C:/LBT/tesisfisica/criostato/Archivos/iv/1312/"  # Replace with your folder path
files = get_files_in_folder(folder_path)
rmin = []
rmax = []
r0 =[]
rf = []
N = []
rcont = []
tcont = []
icont = []
n = 0
t0 = 0
fig, ax = plt.subplots(1,1, figsize=(16,4), dpi=200)

lbls = lambda : itertools.cycle(('0','a','b','c','d','e','f','g','h','i','j'))
lbl = lbls()
lb = next(lbl)
lb = next(lbl)
tos = []
for i in files[:]:
    data = np.genfromtxt(folder_path+i, unpack=True, delimiter=',', skip_header=1)
    t, V, I = data[0], data[1], data[2]*1000
    r0.append(V[0]/I[0]*1000)
    rf.append(V[-1]/I[-1]*1000)
    rmin.append(np.min(V/I*1000))
    rmax.append(np.max(V/I*1000))
    rcont += [x for x in V/I*1000]
    icont += [x for x in I]
    tcont += [x+t0 for x in t]
    N.append(i.split('-')[2])
    n += 1
    t0 += t[-1]
    ax.axvline(t0,0,15,c='gray',ls='dashed')
    if i.split('-')[2] in ['d','e', 'f1','h','i','j','p','q','r1','r2']:
        print(i.split('-')[2])
        # ax.text(t0, 0.99, lb, size='15', color='r', ha='right', va='top', rotation=90,
                # transform=ax.get_xaxis_transform())
        lb = next(lbl)
        tos.append(t0)
ax.fill_between(tcont[298:495], -1, 15, color='green', alpha=0.2)
ax.fill_between(tcont[1613:], -1, 15, color='green', alpha=0.2)
# ax.fill_between(t[16:], [-6,-6,-6,-6,-6,-6,-6,-6,-6], [18,18,18,18,18,18,18,18,19], color='green', alpha=0.2)    
# ax.grid(True)
ax.set_ylabel('$R_{inst} (\Omega)$')
ax.set_xlabel('Time (s)')
# Adjust the colorbar to shift cyan to blue around 2.5
# Create a custom colormap from '#084887' (blue) to '#E63946' (red)
blue = LinearSegmentedColormap.from_list('Blues_r', ['#4c86f0', '#E63946'])
norm = mcolors.LogNorm(vmin=0.5, vmax=30)  # Set logarithmic normalization
sc = ax.scatter(tcont, rcont, s=6, c=icont, cmap=blue, norm=norm, label='c')  # Apply normalization
cbar4 = plt.colorbar(sc, ax=ax, ticks=[1.0, 5.0, 10.0, 20.0, 30.0])  # Set specific ticks
cbar4.ax.yaxis.set_major_formatter(ticker.FixedFormatter([1, 5, 10, 15, 20, 25, 30]))  # Ensure ticks match
cbar4.set_label('Current (mA)')

ax.set_xlim(0,2950)
ax.set_ylim(0,15)
plt.savefig('Fig 4.pdf', format='pdf')
save_figure_data(fig, filename="Fig 4")