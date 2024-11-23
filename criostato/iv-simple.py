#%%
from k224 import *
from a34420a import *
import numpy as np
import time
import csv
import matplotlib.pyplot as plt
#%%
icurr = KEITHLEY_224()
ivolt = Agilent34420A()
ivolt.set_range(0.1)
def msr(cu,bias=False):
    icurr.voltage = float(10)
    icurr.current = float(cu)
    icurr.operate = True
    v_iv = ivolt.measure_voltage()
    while float(ivolt.custom_command('*OPC?')) != 1:
        print('opc?1')
    icurr.operate = False
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
    directory = 'C:/tesis git/tesisfisica/criostato/Archivos/iv'
    file_path = directory +'/'+ file_name + '.csv'
    with open(file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(values)
#%%
datas = []
curva = np.linspace(1e-3,10e-3, 50)
curva_r = np.linspace(10e-3, 1e-3, 50)
for j in curva:
    data = msr(j)
    time.sleep(1)
    datas.append(data)
    add_row(data, 'iv-x5-d')
for k in curva_r:
    data = msr(k)
    time.sleep(1)
    datas.append(data)
    add_row(data, 'iv-x5-d')
datas = []
curva = np.linspace(-1e-3,-10e-3, 50)
curva_r = np.linspace(-10e-3, -1e-3, 50)
for j in curva:
    data = msr(j)
    time.sleep(1)
    datas.append(data)
    add_row(data, 'iv-x5-d-n')
for k in curva_r:
    data = msr(k)
    time.sleep(1)
    datas.append(data)
    add_row(data, 'iv-x5-d-n')
#%%
V, I, Vb, Ib = np.loadtxt('C:/tesis git/tesisfisica/criostato/Archivos/iv/iv-x5-d.csv', delimiter=',', unpack=True)
Vn, In, Vbn, Ibn = np.loadtxt('C:/tesis git/tesisfisica/criostato/Archivos/iv/iv-x5-d-n.csv', delimiter=',', unpack=True)

from scipy.optimize import curve_fit
def r(V,R):
    return V/R

popt, pcov = curve_fit(r, V, I, p0=2)
poptn, pcovn = curve_fit(r,Vn, In, p0=2)
x = np.linspace(0.0015,0.018,100)
xn = np.linspace(-0.0015,-0.018,100)
plt.scatter(V,I)
#plt.scatter(Vn, np.abs(In), color='blue')
plt.grid()
plt.plot(x, r(x, popt),color = 'orange')
plt.yscale('log')
#plt.plot(xn, np.abs(r(xn, poptn)),color = 'red')
plt.title(f'+r = {popt} $\Omega$ -r = {poptn} $\Omega$')
plt.show
# %%
plt.grid()
# %%
