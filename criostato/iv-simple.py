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

def msr(cu,bias=True):
    tem = time.time()
    if bias == True:
        true_v = []
        v_bias = []
        sent_i = []
        icurr.current = float(cu)
        med_v = ivolt.measure_voltage()
        while float(ivolt.custom_command('*OPC?')) != 1:
            print('opc?1')
        v_bias.append(np.abs(med_v))
        sent_i.append(np.abs(float(cu)))
        print(str(time.time()-tem)+'Pulso +')
        icurr.operate = False
        time.sleep(1-(time.time()-tem))
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
        time.sleep(1-(time.time()-tem))
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
    directory = 'C:/tesis git/tesisfisica/criostato/Archivos/iv/1312'
    file_path = directory +'/'+ file_name + '.csv'
    with open(file_path, mode='a+', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(values)
#%%
datas = []
min = 1e-3
max = 20e-3
ctd = 50
tt = time.time()
curva = np.linspace(min,max, ctd)
curva_r = np.linspace(max, min, ctd)
name = 'iv-x5-a-10K'
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
    datas.append(data)
    add_row(data, f'{name}')
    x_datar.append(data[0])
    y_datar.append(data[1])
    liner.set_xdata(x_datar)
    liner.set_ydata(y_datar)
    if data[0] > ax.get_xlim()[1]:
        ax.set_xlim(0, data[0]*1.2)
    if data[1] > ax.get_ylim()[1]:
        ax.set_ylim(0, data[1]*1.2)
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
    if data[0] < ax.get_xlim()[0]:
        ax.set_xlim(data[0]*1.2, ax.get_xlim()[1])
    if data[1] < ax.get_ylim()[0]:
        ax.set_ylim(data[1]*1.2, ax.get_ylim()[1])
    fig.canvas.flush_events()
    plt.pause(0.1)
#%%
for i in ['c-207K']:
    nm=i
    V, I, Vb, Ib = np.loadtxt(f'C:/tesis git/tesisfisica/criostato/Archivos/iv/2911/iv-x5-{nm}.csv', delimiter=',', unpack=True)
    #Vn, In, Vbn, Ibn = np.loadtxt(f'C:/tesis git/tesisfisica/criostato/Archivos/iv/2911/iv-x5-{nm}-n.csv', delimiter=',', unpack=True)
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
    V, I, Vb, Ib = np.loadtxt(f'C:/tesis git/tesisfisica/criostato/Archivos/iv/1012/iv(+-)-x5-{nm}.csv', delimiter=',', unpack=True)
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
