#%%
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.cm as cm
from matplotlib.colors import Normalize
import os
from natsort import natsorted
import matplotlib as mpl
from mpl_toolkits.axes_grid1 import make_axes_locatable

mpl.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10
})

# =========================================================================
# 0. DIRECTORIES & PREREQUISITES 
# =========================================================================
# Set your EIS data directory here
dire = "E:/trabajo/tesis 3/tesisfisica/IVs/1812/ZdeW_1234_18-12-24/"

try:
    files = [f for f in natsorted(os.listdir(dire)) if os.path.isdir(os.path.join(dire, f))]
except FileNotFoundError:
    files = []
    print(f"Warning: Directory {dire} not found!")

def z(w, R1, L1, C1, R2, C2, R3, C3):
    w = 2*np.pi*w
    return 1/(1/R1+1/(1j*w*L1)+1j*w*C1)+1/(1/R2+1j*w*C2)+1/(1/R3+1j*w*C3)

# =========================================================================
# 1. LOAD & PARSE PARAMETERS
# =========================================================================
data_params = np.genfromtxt('e:/trabajo/tesis 3/tesisfisica/eisanalyser/eis/Parametros_ajustados_cx5b.csv', 
                            dtype=str, unpack=True, delimiter=',', skip_header=1)

T_params, Rl, Ll, Cl, Rn, Cn, Ra, Ca = data_params

def split_mag_err(arr):
    mag, err = [], []
    for val in arr:
        if isinstance(val, bytes): val = val.decode()
        if '@' in val:
            m, e = val.split('@')
            mag.append(float(m))
            err.append(float(e))
        else:
            mag.append(float(val))
            err.append(np.nan)
    return np.array(mag), np.array(err)

T_params = T_params.astype(float)
Rl, Rl_err = split_mag_err(Rl)
Ll, Ll_err = split_mag_err(Ll)
Cl, Cl_err = split_mag_err(Cl)
Rn, Rn_err = split_mag_err(Rn)
Cn, Cn_err = split_mag_err(Cn)
Ra, Ra_err = split_mag_err(Ra)
Ca, Ca_err = split_mag_err(Ca)

params_tuple = (Rl, Ll, Cl, Rn, Cn, Ra, Ca)

def log_transform(val, err):
    val_abs = np.where(np.abs(val) == 0, np.nan, np.abs(val))
    log_val = np.log10(val_abs)
    raw_log_err = err / (val_abs * np.log(10))
    log_err = np.clip(raw_log_err, 0, 1.5)
    return log_val, log_err

log_Rl, log_Rl_err = log_transform(Rl, Rl_err)
log_Rn, log_Rn_err = log_transform(Rn, Rn_err)
log_Ra, log_Ra_err = log_transform(Ra, Ra_err)
log_Cl, log_Cl_err = log_transform(Cl, Cl_err)
log_Cn, log_Cn_err = log_transform(Cn, Cn_err)
log_Ca, log_Ca_err = log_transform(Ca, Ca_err)

def log_tick_formatter(val, pos=None):
    return f"$10^{{{int(val)}}}$"

# =========================================================================
# 2. FIGURE LAYOUT (3x2)
# =========================================================================
fig, axs = plt.subplots(3, 2, figsize=(14, 8), dpi=300)

ax_nyq  = axs[0, 0]
ax_bmag = axs[1, 0]
ax_bphs = axs[2, 0]

ax_R    = axs[0, 1]
ax_L    = axs[1, 1]
ax_C    = axs[2, 1]

# =========================================================================
# 3. PLOT LEFT COLUMN (RAW EIS DATA & FITS)
# =========================================================================
# Setup Hot-Cold Colormap
norm = Normalize(vmin=np.nanmin(T_params), vmax=np.nanmax(T_params))
cmap = cm.get_cmap('coolwarm')

if files:
    for n, i in enumerate(files[::-1]):
        try:
            T_str = i.split('_')[-3].split('.')[0]
            T_val = float(T_str)
            
            data_eis = np.genfromtxt(f'{dire}/{i}/Offset_0.00_mV.txt', delimiter=',', skip_header=1)
            w = data_eis[1:, 0]
            re = data_eis[1:, 1]
            im = data_eis[1:, 3]

            color = cmap(norm(T_val))
            
            # Plot Raw Data
            ax_nyq.scatter(re, -im, s=14, color=color, alpha=0.8)
            ax_bmag.scatter(w, np.sqrt(re**2 + im**2), s=14, color=color, alpha=0.8)
            ax_bphs.scatter(w, np.arctan2(im, re), color=color, s=14, alpha=0.8)
            
            # Calculate and Plot Fits
            z_vals = z(w, *(param[n] for param in params_tuple))
            
            ax_nyq.plot(z_vals.real, -z_vals.imag, color=color, alpha=0.8, zorder=3)
            ax_bmag.plot(w, np.sqrt(z_vals.real**2 + z_vals.imag**2), color=color, alpha=0.8, zorder=3)
            ax_bphs.plot(w, np.arctan2(z_vals.imag, z_vals.real), color=color, alpha=0.8, zorder=3)
            
        except Exception as e:
            print(f"Skipping {i}: {e}")

# Add a Horizontal Colorbar specifically on top of the Nyquist Plot
sm = cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])

divider = make_axes_locatable(ax_nyq)
cbar_ax = divider.append_axes("top", size="5%", pad=0.15)
cbar = fig.colorbar(sm, cax=cbar_ax, orientation="horizontal")
cbar_ax.xaxis.set_ticks_position('top')
cbar_ax.xaxis.set_label_position('top')
cbar.set_label('Temperature (K)')

# Format Left Column
ax_nyq.set_xlabel("$Z'$ ($\Omega$)")
ax_nyq.set_ylabel("$-Z''$ ($\Omega$)")
ax_nyq.set_xlim(-4,4)
ax_nyq.set_ylim(-10,15)
# ax_nyq.grid(True, alpha=0.5)

ax_bmag.set_xlabel(" ")
ax_bmag.set_ylabel("$|Z|$ ($\Omega$)")
ax_bmag.set_xscale('log')
ax_bmag.set_yscale('log')
ax_bmag.set_ylim(1.7e0, 2.8e1)
# ax_bmag.grid(True, alpha=0.5)

ax_bphs.set_xlabel("$f$ (Hz)")
ax_bphs.set_ylabel("$\\theta$ (rad)")
ax_bphs.set_xscale('log')
ax_bphs.set_ylim(-2.1, 0.5)
# ax_bphs.grid(True, alpha=0.5)

# =========================================================================
# 4. PLOT RIGHT COLUMN (PARAMETERS)
# =========================================================================

# 4A. Resistance    
ax_R.plot(1/T_params, log_Rl, 'o-', label='$R$', c='#e07b67')
ax_R.plot(1/T_params, log_Rn, 'o-', label='$R_{neg}$', c="#67e08f")
ax_R.plot(1/T_params, log_Ra, 'o-', label='$R_{est}$', c="#6f67e0")

ax_R.set_ylabel('Resistance ($\Omega$)')
ax_R.set_xlabel('1/T (K$^{-1}$)')
ax_R.yaxis.set_major_formatter(ticker.FuncFormatter(log_tick_formatter))
ax_R.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
ax_R.legend(frameon=False)
# ax_R.grid(True, alpha=0.5)

# 4B. Inductance
ax_L.plot(T_params, Ll, 'o-', label='$L$', c='#e07b67')
ax_L.set_ylabel('Inductance (H)')
ax_L.set_xlabel(' ')
ax_L.invert_xaxis()
ax_L.legend(frameon=False)
# ax_L.grid(True, alpha=0.5)

# 4C. Capacitance
ax_C.plot(T_params, log_Cl, 'o-', label='$C$', c='#e07b67')
ax_C.plot(T_params, log_Cn, 'o-', label='$C_{neg}$', c="#67e08f")
ax_C.plot(T_params, log_Ca, 'o-', label='$C_{est}$', c="#6f67e0")

ax_C.set_ylabel('Capacitance (F)')
ax_C.set_xlabel('Temperature (K)')
ax_C.invert_xaxis()
ax_C.yaxis.set_major_formatter(ticker.FuncFormatter(log_tick_formatter))
ax_C.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
ax_C.legend(frameon=False)
# ax_C.grid(True, alpha=0.5)

# =========================================================================
# 5. FINAL RENDER & EXPORT
# =========================================================================
# Notice: 'left' is decreased from 0.18 to 0.10 since the vertical colorbar is gone
plt.subplots_adjust(left=0.10, right=0.95, top=0.92, bottom=0.08, wspace=0.3, hspace=0.25)
plt.savefig('Fig 11.pdf', format='pdf')
plt.show()

try:
    from figure_editor import save_figure_data
    save_figure_data(fig, filename="Fig 11")
except ImportError:
    pass
#%%