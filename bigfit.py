#%%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import os
from os.path import abspath, dirname
#%%
%matplotlib qt
os.chdir('E:/porno/tesis 3/tesisfisica')

def get_files_with_path(folder):
    print(folder)
    return [os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]

def list_folders_in_folder(folder_path):
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]

def newoff(y):
        indices = np.argmin(np.abs(y))
        return indices

def sclc_p(x, A, R):
    return A*np.abs(x)**2+x/R

# def sclc_s(x, A, R, n):
#     return A()

archivo_actual = '/criostato/Archivos/iv/1012/iv(ac20hz)-x5-c-95K.csv'
channel = 'crio'
files = ['255.txt']
fig = plt.figure(figsize=(12, 6))
for i in files:
    channel = 'crio'
    modo = 't'
    data = np.genfromtxt(os.getcwd()+archivo_actual, delimiter='\t', skip_header=1, unpack=True)
    data_t = np.genfromtxt(os.getcwd()+archivo_actual, delimiter='\t', dtype='str', unpack=True)
    if '(K)' in data_t[1][0]:
        modo = 'si_t'
    elif '(K)' not in data_t[1][0]:
        modo = 'no_t'
    else:
        print('ups')
    if channel == '1':
        try:
            if modo == 'no_t':
                indoff = newoff(data[1][~np.isnan(data[1])])
                time = data[0][~np.isnan(data[0])] #tiempo
                ipul = data[1][~np.isnan(data[1])] #I pulso
                try:
                    vin1 = np.array(data[2][~np.isnan(data[2])])-np.array(data[2][~np.isnan(data[2])][indoff]) #V instant
                except IndexError:
                    vin1 = np.array(data[2][~np.isnan(data[2])])
                iin1 = data[3][~np.isnan(data[3])]*1000 #I instant
                rin1 = data[4][~np.isnan(data[4])] #R instant
                rre1 = data[5][~np.isnan(data[5])] #R remanente
                ibi1 = data[6][~np.isnan(data[6])] #I bias
                vbi1 = data[7][~np.isnan(data[7])] #V bias
                wpul = data[14][~np.isnan(data[14])] #ancho pulso
                peri = data[15][~np.isnan(data[15])] #periodo
                temperatura = 'T_amb'
            elif modo == 'si_t':
                indoff = newoff(data[2][~np.isnan(data[2])])
                time = data[0][~np.isnan(data[0])] #tiempo
                temp = data[1][~np.isnan(data[1])] #temp(k)
                ipul = data[2][~np.isnan(data[2])] #I pulso
                try:
                    vin1 = np.array(data[3][~np.isnan(data[3])])-(data[3][~np.isnan(data[3])][indoff[0]-1]+data[3][~np.isnan(data[3])][indoff[0]+1])/2 #V instant
                except IndexError:
                    vin1 = np.array(data[3][~np.isnan(data[3])])
                iin1 = data[4][~np.isnan(data[4])] #I instant
                rin1 = data[5][~np.isnan(data[5])] #R instant
                rre1 = data[6][~np.isnan(data[6])] #R remanente
                ibi1 = data[7][~np.isnan(data[7])] #I bias
                vbi1 = data[8][~np.isnan(data[8])] #V bias
                wpul = data[15][~np.isnan(data[15])] #ancho pulso
                peri = data[16][~np.isnan(data[16])] #periodo
                temperatura = temp[0]
        except Exception as e:
            print(e)
    elif channel=='2':
        if modo == 'no_t':
            iin1 = data[9][~np.isnan(data[9])] #I instant
            indoff = newoff(iin1)
            time = data[0][~np.isnan(data[0])] #tiempo
            ipul = data[1][~np.isnan(data[1])] #I pulso
            try:
                vin1 = np.array(data[8][~np.isnan(data[9])])-np.array(data[9][~np.isnan(data[9])][indoff]) #V instant
            except IndexError:
                vin1 = np.array(data[8][~np.isnan(data[9])])
            rin1 = data[10][~np.isnan(data[10])] #R instant
            rre1 = data[11][~np.isnan(data[11])] #R remanente
            ibi1 = data[12][~np.isnan(data[12])] #I bias
            vbi1 = data[13][~np.isnan(data[13])] #V bias
            wpul = data[14][~np.isnan(data[14])] #ancho pulso
            peri = data[15][~np.isnan(data[15])] #periodo
            temperatura = 'T_amb'
        elif modo == 'si_t':
            indoff = newoff(data[2][~np.isnan(data[2])])
            time = data[0][~np.isnan(data[0])] #tiempo
            temp = data[1][~np.isnan(data[1])] #temp(k)
            ipul = data[2][~np.isnan(data[2])] #I pulso
            try:
                vin1 = np.array(data[9][~np.isnan(data[9])])-np.array(data[9][~np.isnan(data[9])][indoff]) #V instant
            except IndexError:
                vin1 = np.array(data[9][~np.isnan(data[9])])
            iin1 = data[10][~np.isnan(data[10])] #I instant
            rin1 = data[11][~np.isnan(data[11])] #R instant
            rre1 = data[12][~np.isnan(data[12])] #R remanente
            ibi1 = data[13][~np.isnan(data[13])] #I bias
            vbi1 = data[14][~np.isnan(data[14])] #V bias
            wpul = data[15][~np.isnan(data[15])] #ancho pulso
            peri = data[16][~np.isnan(data[16])] #periodo
            temperatura = temp[0]
    elif channel == 'crio':
        data = np.genfromtxt(os.getcwd()+archivo_actual, delimiter=',', skip_header=1, unpack=True)
        indoff = 0
        vin1 = np.array(data[0][~np.isnan(data[0])])
        iin1 = data[1][~np.isnan(data[1])]*1000 #I instant
        ibi1 = data[3][~np.isnan(data[3])]*1000 #I bias
        vbi1 = data[2][~np.isnan(data[0])] #V bias
        time = np.linspace(0,1,len(iin1)) #tiempo
        temperatura = archivo_actual.split('-')[-1]
        if 'nplc' in archivo_actual:
            data = np.genfromtxt(os.getcwd()+archivo_actual, delimiter=',', skip_header=1, unpack=True)
            indoff = 0
            time = data[0][~np.isnan(data[0])]
            vin1 = np.array(data[1][~np.isnan(data[1])])
            iin1 = data[2][~np.isnan(data[2])]*1000 #I instant
            vbi1 = data[3][~np.isnan(data[3])] #V bias
            ibi1 = data[4][~np.isnan(data[4])]*1000 #I bias
            temperatura = archivo_actual.split('-')[-2]
        rin1 = np.array(vin1)/np.array(iin1)*1000
        print('hola')
    # iin1 = [np.abs(iin1[j]) for j in np.arange(len(iin1)) if vin1[j]>0]
    # vin1 = [j for j in vin1 if j>0]
    plt.scatter(vin1,iin1, label='Experimental')
    # popt, pcov = curve_fit(sclc_p, vin1, iin1, sigma=np.full_like(iin1, 0.05e-1), p0=[1,3], absolute_sigma = True, bounds=[[0,0],[1e3,100e3]])
    # A, R = popt[0], popt[1]
    # plt.plot(vin1, sclc_p(vin1, *popt), label='Ajuste', c='r', zorder=10)
v = 'V (V)'
i = 'I (A)'
r = 'R ($\Omega$)'
plt.xlabel(v)
plt.legend()
plt.ylabel(i)
plt.grid()

#%%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import os
from os.path import abspath, dirname
%matplotlib inline
os.chdir('e:/porno/tesis 3/tesisfisica/')

files = ['26-12-ajustes-canal1b.csv']
for i in files:
    fig, ax = plt.subplots(1,1, figsize=(8,5))
    # ax2 = ax.twiny()
    # fig.suptitle(i)
    T = []
    A = []
    Ae = []
    R = []
    Re = []
    R4 = []
    R4e = []
    data = np.genfromtxt(os.getcwd()+'/'+i, delimiter=',', skip_header=1, unpack=True, dtype='str')
    for i in data[0]:
        T.append(float(i))
    for i in data[1]:
        A.append(float(i.split('Â±')[0]))
        Ae.append(float(i.split('Â±')[1]))
    for i in data[2]:
        R.append(float(i.split('Â±')[0]))
        Re.append(float(i.split('Â±')[1]))
    for i in data[3]:
        R4.append(float(i.split('Â±')[0]))
        R4e.append(float(i.split('Â±')[1]))
    T = np.array(T)
    A = np.array(A)
    Ae = np.array(Ae)
    R = np.array(R)
    Re = np.array(Re)
    R4 = np.array(R4)
    R4e = np.array(R4e)
    line1 = ax.errorbar(1/T, np.log(A), yerr=Ae/A, marker='o', markersize=3, label='Log(A)', color='#0CA0DC')
    line2 = ax.errorbar(1/T, np.log(R), yerr=Re/R, marker='o', markersize=3, label='Log($R_{2t}$)', color='#2A9D8F')
    line3 = ax.errorbar(1/T, np.log(R4), yerr=R4e/R4, marker='o', markersize=3, label='Log($R_{4t}$)', color='#E63946')
    ax.set_xlabel('1/T (1/K)')
    # ax.set_ylim(0.5e-1,1e1)
    # ax2.set_xlim(310, 85)
    ax.set_ylabel('Log(R)')
    # ax2.set_ylabel('Log(R)')
    ax.grid()
    lines = [line1, line2, line3]
    labels = [line.get_label() for line in lines]
    ax.legend(lines, labels, loc='right')

files = ['14-11-ajustes-canal1b.csv']
for i in files:
    # ax2 = ax.twiny()
    # fig.suptitle(i)
    T = []
    A = []
    Ae = []
    R = []
    Re = []
    R4 = []
    R4e = []
    data = np.genfromtxt(os.getcwd()+'/'+i, delimiter=',', skip_header=1, unpack=True, dtype='str')
    for i in data[0]:
        T.append(float(i))
    for i in data[1]:
        A.append(float(i.split('Â±')[0]))
        Ae.append(float(i.split('Â±')[1]))
    for i in data[2]:
        R.append(float(i.split('Â±')[0]))
        Re.append(float(i.split('Â±')[1]))
    for i in data[3]:
        R4.append(float(i.split('Â±')[0]))
        R4e.append(float(i.split('Â±')[1]))
    T = np.array(T)
    A = np.array(A)
    Ae = np.array(Ae)
    R = np.array(R)
    Re = np.array(Re)
    R4 = np.array(R4)
    R4e = np.array(R4e)
    line1 = ax.errorbar(1/T, np.log(A), yerr=Ae/A, marker='none', linestyle='dashed', markersize=3, label='Log(A)', color='#0CA0DC')
    line2 = ax.errorbar(1/T, np.log(R), yerr=Re/R, marker='none', linestyle='dashed', markersize=3, label='Log($R_{2t}$)', color='#2A9D8F')
    line3 = ax.errorbar(1/T, np.log(R4), yerr=R4e/R4, marker='none', linestyle='dashed', markersize=3, label='Log($R_{4t}$)', color='#E63946')
    # ax.set_xlabel('1/T (1/K)')
    # # ax.set_ylim(0.5e-1,1e1)
    # # ax2.set_xlim(310, 85)
    # ax.set_ylabel('Log(R)')
    # # ax2.set_ylabel('Log(R)')
    # ax.grid()
    # lines = [line1, line2, line3]
    # labels = [line.get_label() for line in lines]
    # ax.legend(lines, labels, loc='right')

    # ax.set_yscale('log')

# %%
