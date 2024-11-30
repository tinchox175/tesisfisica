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
ivolt.set_range(0.1)

def msr(cu,bias=False):
    icurr.voltage = float(10)
    icurr.current = float(cu)
    tem = time.time()
    icurr.operate = True
    v_iv = ivolt.measure_voltage()
    while float(ivolt.custom_command('*OPC?')) != 1:
        print('opc?1')
    #icurr.operate = False
    print(time.time()-tem)
    if bias == True:
        v_bias = []
        sent_i = []
        icurr.voltage = float(10)
        icurr.current = float(0.001)
        icurr.operate = True
        time.sleep(1)
        med_v = ivolt.measure_voltage()
        while float(ivolt.custom_command('*OPC?')) != 1:
            print('opc?1')
        v_bias.append(np.abs(med_v))
        sent_i.append(np.abs(float(0.001)))
        icurr.current = -float(0.001)
        icurr.operate = True
        med_v = ivolt.measure_voltage()
        while float(ivolt.custom_command('*OPC?')) != 1:
            print('opc?2')
        v_bias.append(np.abs(med_v))
        sent_i.append(np.abs(float(0.001)))
        icurr.operate = False
        v_bias = np.mean(v_bias)
        i_mean = np.mean(sent_i)
    else:
        v_bias = 0
    return [v_iv, cu,v_bias, 0.001]

def add_row(values, file_name, ctrl=0):
    directory = 'C:/tesis git/tesisfisica/criostato/Archivos/iv/2911'
    file_path = directory +'/'+ file_name + '.csv'
    with open(file_path, mode='a+', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(values)
#%%
datas = []
min = 1e-3
max = 50e-3
ctd = 200
curva = np.linspace(min,max, ctd)
curva_r = np.linspace(max, min, ctd)
name = 'iv-x5-e-150K'
plt.ion()  # Turn on interactive mode
fig, ax = plt.subplots()
line, = ax.plot([], [], 'b-o', linewidth=0.5, markersize=4, marker='x')
ax.set_xlim(0,0.002)
ax.set_ylim(-min,min)
ax.set_xlabel("Voltaje (V)")
ax.set_ylabel("Corriente (A)")
ax.legend()
ax.grid(True)
x_data = []
y_data = []
for j in curva:
    data = msr(j)
    time.sleep(1)
    datas.append(data)
    add_row(data, f'{name}')
    x_data.append(data[0])
    y_data.append(data[1])
    line.set_xdata(x_data)
    line.set_ydata(y_data)
    if data[0] > ax.get_xlim()[1]:
        ax.set_xlim(0, data[0]*1.2)
    if data[1] > ax.get_ylim()[1]:
        ax.set_ylim(0, data[1]*1.2)
    fig.canvas.flush_events()
    plt.pause(0.1)
for k in curva_r:
    data = msr(k)
    time.sleep(1)
    datas.append(data)
    add_row(data, f'{name}')
    x_data.append(data[0])
    y_data.append(data[1])
    line.set_xdata(x_data)
    line.set_ydata(y_data)
    if data[0] > ax.get_xlim()[1]:
        ax.set_xlim(0, data[0]*1.2)
    if data[1] > ax.get_ylim()[1]:
        ax.set_ylim(0, data[1]*1.2)
    fig.canvas.flush_events()
    plt.pause(0.1)
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
    if data[0] < ax.get_xlim()[0]:
        ax.set_xlim(data[0]*1.2, ax.get_xlim()[1])
    if data[1] < ax.get_ylim()[0]:
        ax.set_ylim(data[1]*1.2, ax.get_ylim()[1])
    fig.canvas.flush_events()
    plt.pause(0.1)
#%%
nm='d'
V, I, Vb, Ib = np.loadtxt(f'C:/tesis git/tesisfisica/criostato/Archivos/iv/2911/iv-x5-{nm}.csv', delimiter=',', unpack=True)
Vn, In, Vbn, Ibn = np.loadtxt(f'C:/tesis git/tesisfisica/criostato/Archivos/iv/2911/iv-x5-{nm}-n.csv', delimiter=',', unpack=True)

from scipy.optimize import curve_fit
def r(V,R):
    return V/R

popt, pcov = curve_fit(r, V, I, p0=2)
poptn, pcovn = curve_fit(r,Vn, In, p0=2)
x = np.linspace(0.002,0.15,100)
xn = np.linspace(-0.0025,-0.15,100)
plt.figure()
plt.scatter(V, I)
#plt.scatter(V[:int(len(V)/2)+23],I[:int(len(V)/2)+23])
#plt.scatter(V[int(len(V)/2)+23:-1],I[int(len(V)/2)+23:-1])
plt.scatter(Vn, In)
#plt.scatter(Vn, np.abs(In), color='blue')
plt.xlim(-0.5,0.5)
plt.grid()
plt.plot(x, r(x, popt),color = 'orange')
#plt.yscale('log')
#plt.plot(xn, (r(xn, poptn)),color = 'red')
#plt.title(f'+r = {popt} $\Omega$ -r = {poptn} $\Omega$')
plt.show
# %%
plt.grid()
# %%
