#%%
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import matplotlib
import scipy.signal
window_size=400
matplotlib.rcParams.update({'font.size': 14})
%matplotlib qt
off = [0,0.05,0.1,0.15,0.2,0,0.05,0.1,0.15,0.2]
m=0
f = 1e3
dv12 = []
dv12e = []
dv3 = []
dv3e = []
dv34 = []
dv34e = []
for n in ['09','10','11','12','13','28','29','30','31','32']:
#for n in ['09',10,11,12,13]:
    fr, c1, c2, c3, c4 = np.genfromtxt(f'./IVs/2611/B/tek00{n}ALL.csv', unpack=True, delimiter=',', skip_header=20)
    x = fr[3500:-2000]
    y1 = c1[3500:-2000]
    y2 = c2[3500:-2000]
    y1 = scipy.signal.savgol_filter(y1, window_size, 6)
    y2 = scipy.signal.savgol_filter(y2, window_size, 6)
    def sine_function(x, A, omega, phi, C):
        return A * np.sin(omega * x + phi) + C
    po = [0.2, f*2*np.pi, 0, off[m]]
    popt1, pcov1 = curve_fit(sine_function, x, y1, p0=po)
    popt2, pcov2 = curve_fit(sine_function, x, y2, p0=po)
    colord = ['blue','red','orange','purple','yellow','black','pink']
    fig, (ax1, ax3, ax2) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    ax1.scatter(x, y1, label='Canal 1', alpha=0.35, s=5)
    ax1.plot(x, sine_function(x, *popt1), color='red',alpha=0.5, label='Ajuste C1')
    ax1.scatter(x, y2, label='Canal 2', alpha=0.35, s=5)
    ax1.plot(x, sine_function(x, *popt2), color='purple', alpha=0.5, label='Ajuste C2')
    ax1.set_ylabel('Amplitud (V)')
    ax1.grid(True)
    ax3.plot(x, y1-y2, label='C1-C2', color='black')
    ax3.plot(x, sine_function(x,*popt1)-sine_function(x,*popt2), label='Aj(C1)-Aj(C2)', color='green')
    ax3.grid(True)
    ax3.set_ylabel('Diferencia (V)')
    residuals1 = y1 - sine_function(x, *popt1)
    residuals2 = y2 - sine_function(x, *popt2)
    ax2.plot(x, residuals1, alpha=0.5, color='red', label='Residuos C1')
    ax2.plot(x, residuals2, alpha=0.5, color='purple', label='Residuos C2')
    ax2.set_xlabel('Tiempo (s)')
    ax2.set_ylabel('Residuos (V)')
    ax2.axhline(0, color='black', linestyle='--', linewidth=1)
    ax2.grid(True)
    if m==0:
        ax1.legend()
        ax2.legend()
        ax3.legend()
    curr = (np.max(sine_function(x,*popt1)-sine_function(x,*popt2)))/33
    dv12.append(np.max(sine_function(x, *popt1))-np.max(sine_function(x, *popt2)))
    sigmai = np.abs(np.max(sine_function(x,*popt1)-sine_function(x,*popt2))-np.max(y1-y2))/33
    plt.suptitle(f'{n} 1-2 Max $\Delta V$ = {np.round(np.max(sine_function(x, *popt1))-np.max(sine_function(x, *popt2)),2)} V')
    plt.tight_layout()
    #plt.savefig(f'{n} 1-2')
    y1 = c2[3500:-2000]
    y1 = scipy.signal.savgol_filter(y1, window_size, 3)
    po = [0.1, f*2*np.pi, 0, off[m]]
    popt1, pcov1 = curve_fit(sine_function, x, y1, p0=po)
    popt2, pcov2 = curve_fit(sine_function, x, y2, p0=po)
    colord = ['blue','red','orange','purple','yellow','black','pink']
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    ax1.scatter(x, y1, label='Canal 2', alpha=0.35, s=5)
    ax1.plot(x, sine_function(x, *popt1), color='red',alpha=0.5, label='Ajuste C2')
    ax1.set_ylabel('Amplitud (V)')
    ax1.grid(True)
    residuals1 = y1 - sine_function(x, *popt1)
    residuals2 = y2 - sine_function(x, *popt2)
    ax2.plot(x, residuals1, alpha=0.5, color='red', label='Residuos C2')
    ax2.set_xlabel('Tiempo (s)')
    ax2.set_ylabel('Residuos (V)')
    ax2.axhline(0, color='black', linestyle='--', linewidth=1)
    ax2.grid(True)
    if m==0:
        ax1.legend()
        ax2.legend()
        ax3.legend()
    dv3.append(np.max(sine_function(x, *popt1)))
    v3 = (np.max(sine_function(x, *popt1)))
    sigma3 = np.abs(np.max(sine_function(x,*popt1))-np.max(y1))/33
    dv3e.append(np.sqrt((sigma3/curr)**2+(sigmai*v3/curr**2)**2))
    plt.suptitle(f'{n} 2-3 Max $\Delta V$ = {np.round(np.max(sine_function(x, *popt1)),4)} V')
    plt.tight_layout()
    #plt.savefig(f'{n} 2-3')
    y1 = c3[3500:-2000]
    y2 = c4[3500:-2000]
    y1 = scipy.signal.savgol_filter(y1, window_size, 3)
    y2 = scipy.signal.savgol_filter(y2, window_size, 3)
    po = [0.1, f*2*np.pi, 0, off[m]]
    popt1, pcov1 = curve_fit(sine_function, x, y1, p0=po)
    popt2, pcov2 = curve_fit(sine_function, x, y2, p0=po)
    colord = ['blue','red','orange','purple','yellow','black','pink']
    fig, (ax1, ax3, ax2) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    ax1.scatter(x, y1, label='Canal 3', alpha=0.35, s=5)
    ax1.plot(x, sine_function(x, *popt1), color='red',alpha=0.5, label='Ajuste C3')
    ax1.scatter(x, y2, label='Canal 4', alpha=0.35, s=5)
    ax1.plot(x, sine_function(x, *popt2), color='purple', alpha=0.5, label='Ajuste C4')
    ax1.set_ylabel('Amplitud (V)')
    ax1.grid(True)
    ax3.plot(x, y1-y2, label='C3-C4', color='black')
    ax3.plot(x, sine_function(x,*popt1)-sine_function(x,*popt2), label='Aj(C3)-Aj(C4)', color='green')
    ax3.grid(True)
    ax3.set_ylabel('Diferencia (V)')
    residuals1 = y1 - sine_function(x, *popt1)
    residuals2 = y2 - sine_function(x, *popt2)
    ax2.plot(x, residuals1, alpha=0.5, color='red', label='Residuos C3')
    ax2.plot(x, residuals2, alpha=0.5, color='purple', label='Residuos C4')
    ax2.set_xlabel('Tiempo (s)')
    ax2.set_ylabel('Residuos (V)')
    ax2.axhline(0, color='black', linestyle='--', linewidth=1)
    ax2.grid(True)
    if m==0:
        ax1.legend()
        ax2.legend()
        ax3.legend()
    m+=1
    dv34.append(np.max(sine_function(x,*popt1)-sine_function(x,*popt2)))
    sigma34 = np.abs(np.max(sine_function(x,*popt1)-sine_function(x,*popt2))-np.max(y1-y2))/33
    v34 = (np.max(sine_function(x,*popt1)-sine_function(x,*popt2)))
    dv34e.append(np.sqrt((sigma34/curr)**2+(sigmai*v34/curr**2)**2))
    plt.suptitle(f'{n} 3-4 Max $\Delta V$ = {np.round(np.max(sine_function(x, *popt1))-np.max(sine_function(x, *popt2)),4)} V')
    plt.tight_layout()
    #plt.savefig(f'{n} 3-4')
#plt.show()

# %%
dv12 = np.array(dv12) #v
dv23 = np.array(dv3) #v
dv34 = np.array(dv34) #v
off = [0,0.05,0.1,0.15,0.2,0,0.05,0.1,0.15,0.2]
R = 33 #ohm
i = dv12/R #amp
R2T = dv23/i #ohm
R4T = dv34/i #ohm
fig, ax1 = plt.subplots(figsize=(10,8))
ax1.plot(off[0:5], R2T[0:5], linestyle='--', color='purple', marker='o', linewidth=0.5, markersize=5, label='R 2 term. 300K')
ax1.errorbar(off[0:5], R2T[0:5], yerr=dv3e[0:5], color='purple', fmt='none')
ax1.plot(off[5:9], R2T[5:9], linestyle='--', color='magenta', marker='o', linewidth=0.5, markersize=5, label='R 2 term. 200K')
ax1.errorbar(off[5:9], R2T[5:9], yerr=dv3e[5:9], color='magenta', fmt='none')
ax1.set_ylabel('Resistencia ($\Omega$)')
ax1.set_xlabel('Offset (V)')
ax1.grid(True)
ax1.legend()
plt.suptitle(f'$f={f} Hz$ $T = 300 K$ $A=200mV$')
fig, ax1 = plt.subplots(figsize=(10,8))
ax1.plot(off[0:5], R4T[0:5], linestyle='--', color='red', marker='o', linewidth=0.5, markersize=5, label='R 4 term. 300K')
ax1.errorbar(off[0:5], R4T[0:5], yerr=dv34e[0:5], color='red', fmt='none')
ax1.plot(off[5:9], R4T[5:9], linestyle='--', color='orange', marker='o', linewidth=0.5, markersize=5, label='R 4 term. 200K')
ax1.errorbar(off[5:9], R4T[5:9], yerr=dv34e[5:9], color='orange', fmt='none')
ax1.set_ylabel('Resistencia ($\Omega$)')
ax1.set_xlabel('Offset (V)')
ax1.grid(True)
ax1.legend()
plt.suptitle(f'$f={f} Hz$ $T = 300 K$ $A=200mV$')
plt.tight_layout()
plt.show()
# %%
