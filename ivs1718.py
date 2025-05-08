import numpy as np
import matplotlib.pyplot as plt
import time
import os
from scipy.signal import savgol_filter
%matplotlib qt
def get_files_with_path(folder):
    print(folder)
    return [os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]
data_tot = []
dir = get_files_with_path('E:/porno/tesis 3/tesisfisica/IVs/escrituras')
tiempo = np.array([])
ipul = np.array([])
rinst = np.array([])
rrem = np.array([])
vinst = np.array([])
rinst2 = np.array([])
rrem2 = np.array([])
vinst2 = np.array([])
vlines = []
for i in dir[:-2]:
    data = np.genfromtxt(i, unpack=True, skip_header=1)
    try:
        vlines.append(data[0][-1]+tiempo[-1])
        tiempo = np.append(tiempo, data[0]+tiempo[-1]) 
    except:
        vlines.append(data[0][-1])
        tiempo = np.append(tiempo, data[0]) 
    rinst = np.append(rinst, data[4]) 
    rrem = np.append(rrem, data[5]) 
    vinst = np.append(vinst, data[2]) 
    rinst2 = np.append(rinst2, data[10]) 
    rrem2 = np.append(rrem2, data[11]) 
    vinst2 = np.append(vinst2, data[2]) 

plt.figure(figsize=(12,8))
plt.title('Switcheo 2t')
plt.scatter(vinst, rinst, label='R instantanea')
plt.scatter(vinst, rrem, label='R remanente')
for i in vlines:
    plt.vlines(i, 0, 1e5, color='grey', linestyles='dashed')
plt.yscale('log')
plt.ylim(np.min([np.min(rinst), np.min(rrem)]), np.max([np.max(rinst), np.max(rrem)]))
plt.xlim(np.min(vinst)-3, np.max(vinst)+3)
plt.grid()
plt.xlabel('Tiempo (s)')
plt.ylabel('R (Ohm)')
plt.legend()
plt.figure(figsize=(12,8))
plt.title('Switcheo 4t')
rrem2 = savgol_filter(rrem2, window_length=50, polyorder=1)
plt.scatter(vinst2, rinst2, label='R instantanea')
plt.scatter(vinst2, rrem2, label='R remanente')
for i in vlines:
    plt.vlines(i, 0, 1e5, color='grey', linestyles='dashed')
plt.yscale('log')
plt.ylim(np.min([np.min(rinst2), np.min(rrem2)]), np.max([np.max(rinst2), np.max(rrem2)]))
plt.xlim(np.min(vinst2)-3, np.max(vinst2)+3)
plt.grid()
plt.xlabel('Tiempo (s)')
plt.ylabel('R (Ohm)')
plt.legend()