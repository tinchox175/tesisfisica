#%%
from k224 import *
from a34420a import *
import numpy as np
import time
import csv
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')  # Use the TkAgg backend
#%%
icurr = KEITHLEY_224()
ivolt = Agilent34420A()
ivolt.set_range(1)
icurr.voltage = float(20)
#%%
def msr(cu,bias=True):
    tem = time.time()
    if bias == True:
        true_v = []
        v_bias = []
        sent_i = []
        icurr.current = float(cu)
        icurr.operate = True
        med_v = ivolt.measure_voltage()
        while float(ivolt.custom_command('*OPC?')) != 1:
            print('opc?1')
        v_bias.append(np.abs(med_v))
        sent_i.append(np.abs(float(cu)))
        print(str(time.time()-tem)+'Pulso +')
        icurr.operate = False
        time.sleep(0.5)
        print(str(time.time()-tem)+'Sleep')
        icurr.current = -float(cu)
        icurr.operate = True
        med_v = ivolt.measure_voltage()
        while float(ivolt.custom_command('*OPC?')) != 1:
            print('opc?2')
        v_bias.append(np.abs(med_v))
        sent_i.append(np.abs(float(-cu)))
        print(str(time.time()-tem)+'Pulso -')
        icurr.operate = False
        v_bias = np.mean(v_bias)
        v_iv = v_bias
        #print(med_v, v_bias)
        i_mean = np.mean(sent_i)
        time.sleep(0.5)
        print(str(time.time()-tem)+'Sleep')
        print(time.time()-tem)
    else:
        icurr.current = float(cu)
        v_iv = ivolt.measure_voltage()
        while float(ivolt.custom_command('*OPC?')) != 1:
            print('opc?1')
        #icurr.operate = False
        print(time.time()-tem)
        v_bias = 0
    tr = time.time()-tt
    return [tr, v_iv, cu,v_bias, cu]
#%%
def add_row(values, file_name, ctrl=0):
    directory = 'e:/porno/tesis 3//tesis git/tesisfisica/criostato/Archivos/iv/1312'
    file_path = directory +'/'+ file_name + '.csv'
    with open(file_path, mode='a+', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(values)
#%%
datas = []
min = 0.1e-3
max = 25e-3
ctd = 40
tt = time.time()
curva = np.geomspace(min,max, ctd)
curva_r = np.geomspace(max, min, ctd)
name = 'iv-x5-x-14K-2nplc'
#name = 'iv(+-)-x5-test6'
plt.ion()  # Turn on interactive mode
fig, ax = plt.subplots()
line, = ax.plot([], [], 'b-o', linewidth=0.5, markersize=4, marker='x', label='Ida')
liner, = ax.plot([], [], 'r-o', linewidth=0.5, markersize=4, marker='x', label='Vuelta')
ax.set_xlim(0,0.002)
ax.set_ylim(-min,min)
ax.set_xlabel("Voltaje (V)")
ax.set_ylabel("Corriente (A)")
ax.legend()
ax.grid(True)
x_data = []
y_data = []
x_datar = []
y_datar = []
icurr.current = min
icurr.operate = True
for j in curva:
    data = msr(j)
    datas.append(data)
    add_row(data, f'{name}')
    x_data.append(data[1])
    y_data.append(data[2])
    line.set_xdata(x_data)
    line.set_ydata(y_data)
    if data[1] > ax.get_xlim()[1]:
        ax.set_xlim(0, data[1]*1.2)
    if data[2] > ax.get_ylim()[1]:
        ax.set_ylim(0, data[2]*1.2)
    fig.canvas.flush_events()
    plt.pause(0.1)
for k in curva_r:
    data = msr(k)
    datas.append(data)
    add_row(data, f'{name}')
    x_datar.append(data[1])
    y_datar.append(data[2])
    liner.set_xdata(x_datar)
    liner.set_ydata(y_datar)
    if data[1] > ax.get_xlim()[1]:
        ax.set_xlim(0, data[1]*1.2)
    if data[2] > ax.get_ylim()[1]:
        ax.set_ylim(0, data[2]*1.2)
    fig.canvas.flush_events()
    plt.pause(0.1)
icurr.operate = False
#%%
datas = []
curva = np.linspace(-min,-max, ctd)
curva_r = np.linspace(-max, -min, ctd)
for j in curva:
    data = msr(j)
    time.sleep(1)
    datas.append(data)
    add_row(data, f'{name}-n')
    x_data.append(data[0])
    y_data.append(data[1])
    line.set_xdata(x_data)
    line.set_ydata(y_data)
    if data[0] < ax.get_xlim()[0]:
        ax.set_xlim(data[0]*1.2, ax.get_xlim()[1])
    if data[1] < ax.get_ylim()[0]:
        ax.set_ylim(data[1]*1.2, ax.get_ylim()[1])
    fig.canvas.flush_events()
    plt.pause(0.1)
for k in curva_r:
    data = msr(k)
    time.sleep(1)
    datas.append(data)
    add_row(data, f'{name}-n')
    x_data.append(data[0])
    y_data.append(data[1])
    line.set_xdata(x_data)
    line.set_ydata(y_data)
    # if data[0] < ax.get_xlim()[0]:
    #     ax.set_xlim(data[0]*1.2, ax.get_xlim()[1])
    # if data[1] < ax.get_ylim()[0]:
    #     pass
    #     #ax.set_ylim(data[1]*1.2, ax.get_ylim()[1])
    fig.canvas.flush_events()
    plt.pause(0.1)
#%%
for i in ['c-207K']:
    nm=i
    V, I, Vb, Ib = np.loadtxt(f'e:/porno/tesis 3//tesis git/tesisfisica/criostato/Archivos/iv/2911/iv-x5-{nm}.csv', delimiter=',', unpack=True)
    #Vn, In, Vbn, Ibn = np.loadtxt(f'e:/porno/tesis 3//tesis git/tesisfisica/criostato/Archivos/iv/2911/iv-x5-{nm}-n.csv', delimiter=',', unpack=True)
    from scipy.optimize import curve_fit
    def r(V,R):
        return V/R
    popt, pcov = curve_fit(r, V, I, p0=2)
    #poptn, pcovn = curve_fit(r,Vn, In, p0=2)
    x = np.linspace(0.002,np.max(V),len(V)-1)
    #xn = np.linspace(-0.0025,-0.15,100)
    fig, (ax1, ax2) = plt.subplots(2,1, sharex=True)
    #plt.plot(V, I, 'b-o', linewidth=0.5, markersize=2, marker='x')
    ax1.plot(V[:int(len(V)/2)],I[:int(len(V)/2)], 'b-o', linewidth=0.5, markersize=2, marker='x', label='Ida')
    ax1.plot(V[int(len(V)/2):-1],I[int(len(V)/2):-1], 'r-o', linewidth=0.5, markersize=2, marker='x', label='Vuelta')
    #plt.plot(Vn, In)
    #plt.scatter(Vn, np.abs(In), color='blue')
    #plt.xlim(-0.5,0.5)
    ax1.grid(True)
    ax1.plot(V, r(V, popt),color = 'orange', label='Ajuste')
    ax2.plot(V[:int(len(V)/2)], r(V, popt)[:int(len(V)/2)]-I[:int(len(V)/2)], color='black', label='Residuo Ajuste')
    ax2.grid(True)
    ax2.set_xlabel('Voltaje (V)')
    ax1.set_ylabel('Corriente (A)')
    ax2.set_ylabel('Corriente (A)')
    plt.suptitle(f'{nm.split('-')[1]} R={popt} $\Omega$')
    plt.savefig(f'{nm.split('-')[1]}.png')
plt.show()
# %%
p=0
for i in ['a-100K']:
    nm=i
    V, I, Vb, Ib = np.loadtxt(f'e:/porno/tesis 3//tesis git/tesisfisica/criostato/Archivos/iv/1012/iv(+-)-x5-{nm}.csv', delimiter=',', unpack=True)
    from scipy.optimize import curve_fit
    def r(V,R):
        return V/R
    popt, pcov = curve_fit(r, V, I, p0=2)
    x = np.linspace(0.002,np.max(V),len(V)-1)
    fig, (ax1) = plt.subplots(1,1)
    #ax1.plot(V, I, 'b-o', linewidth=0.5, markersize=2, marker='x')
    ax1.plot(V[:int(len(V)/2)+p],I[:int(len(V)/2)+p], 'b-o', linewidth=0.5, markersize=4, marker='x', label='Ida')
    ax1.plot(V[int(len(V)/2)+p:-1],I[int(len(V)/2)+p:-1], 'r-o', linewidth=0.5, markersize=4, marker='x', label='Vuelta')
    ax1.grid(True)
    #ax1.plot(V, r(V, popt),color = 'orange', label='Ajuste')
    ax1.set_xlabel('Voltaje (V)')
    ax1.set_ylabel('Corriente (A)')
    plt.suptitle(f'{nm.split('-')[1]}')
plt.show()
# %%
t = time.time()
for i in np.arange(0,10):
    icurr.current = 1e-3
    icurr.operate = True
    print(ivolt.measure_voltage())
    while float(ivolt.custom_command('*OPC?')) != 1:
            print('opc?1')
    #time.sleep(0.01)
    icurr.operate = False
    time.sleep(0.01)
print(time.time()-t)
# %%
import os
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as mcolors
%matplotlib qt
def get_files_in_folder(folder_path):
    # Get all files in the folder
    return [file for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file))]
folder_path = "e:/porno/tesis 3//tesis git/tesisfisica/criostato/Archivos/iv/1312/"  # Replace with your folder path
files = get_files_in_folder(folder_path)
for i in files[2:]:
    data = np.genfromtxt(folder_path+i, unpack=True, delimiter=',', skip_header=1)
    t, V, I = data[0], data[1], data[2]
    fig, (ax1, ax2) = plt.subplots(2,1, sharex=True, figsize=(12,7))
    sm = ax1.scatter(V,I, c=t, cmap='cool')
    ax1.grid(True)
    ax1.set_xlabel('Voltaje (V)')
    ax1.set_ylabel('Corriente (A)')
    ax2.scatter(V,V/I, c=t, cmap='cool')
    ax2.grid(True)
    ax2.set_xlabel('Voltaje (V)')
    ax2.set_ylabel('Resistencia (Ohm)')
    plt.suptitle(f'{i}')
# %%
import os
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker
import matplotlib.colors as mcolors
import itertools
from matplotlib.colors import LinearSegmentedColormap
%matplotlib inline
def get_files_in_folder(folder_path):
    # Get all files in the folder
    return [file for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file))]
folder_path = "e:/porno/tesis 3//tesisfisica/criostato/Archivos/iv/1312/"  # Replace with your folder path
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
fig, ax = plt.subplots(1,1, figsize=(12,4), dpi=150)
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
        ax.text(t0, 0.99, lb, color='r', ha='right', va='top', rotation=90,
                transform=ax.get_xaxis_transform())
        lb = next(lbl)
        tos.append(t0)
ax.grid(True)
ax.set_ylabel('$R_{inst} (\Omega)$')
ax.set_xlabel('Tiempo (s)')
# Adjust the colorbar to shift cyan to blue around 2.5
# Create a custom colormap from '#084887' (blue) to '#E63946' (red)
blue = LinearSegmentedColormap.from_list('blue_red', ['#4c86f0', '#E63946'])
norm = mcolors.LogNorm(vmin=0.5, vmax=30)  # Set logarithmic normalization
sc = ax.scatter(tcont, rcont, s=6, c=icont, cmap=blue, norm=norm)  # Apply normalization
cbar4 = plt.colorbar(sc, ax=ax, ticks=[1, 5, 10, 15, 20, 25, 30])  # Set specific ticks
cbar4.ax.yaxis.set_major_formatter(ticker.FixedFormatter([1, 5, 10, 15, 20, 25, 30]))  # Ensure ticks match
cbar4.set_label('Corriente (mA)')
ax.set_xlim(0,2950)
ax.set_ylim(0,15)
# ax.legend()
fig, ax = plt.subplots(1,1, figsize=(9,4), dpi=150)
ax.plot(N, r0, c='#4c86f0', lw=5, linestyle='dashed', label='$R_{inicial}$')
ax.plot(N, rf, c='#E63946', lw=5, linestyle='dashed', label='$R_{final}$')
# ax.grid(True)
# ax.set_ylabel('$R_{inst} (\Omega)$')
# ax.set_xlabel('Medición')
# ax.legend()
# fig, ax = plt.subplots(1,1, figsize=(12,7))
ax.scatter(N, rmin, c='#2A9D8F', marker='s', s=150, label='$R_{mín}$')
ax.scatter(N, rmax, c='#C77DFF', marker='s', s=150, label='$R_{máx}$')
ax.grid(True)
# lbls = lambda : itertools.cycle(('0','a','b','c','d','e','f','g','h','i','j'))
# lbl = lbls()
# lb = next(lbl)
# lb = next(lbl)
# for i in len(tos):
#     ax.text(i, 0.99, lb, color='r', ha='right', va='top', rotation=90,
#                 transform=ax.get_xaxis_transform())
#     lb = next(lbl)
ax.set_ylabel('$R (\Omega)$')
ax.set_xlabel('Medición')
# plt.xticks(N,['','a','b','','','','c','d','e','','','','','f','g'
#               ,'h','i','','','','','','','',''])
ax.fill_between(N[3:6], [-6,-6,-6], [18,18,16], color='green', alpha=0.2)
ax.fill_between(N[16:], [-6,-6,-6,-6,-6,-6,-6,-6,-6], [18,18,18,18,18,18,18,18,19], color='green', alpha=0.2)    
ax.set_ylim(0,15)
ax.legend()

plt.tight_layout()
# %%