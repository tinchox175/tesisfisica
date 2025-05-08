import matplotlib.pyplot as plt
import numpy as np
import os
import itertools
marker_l = lambda : itertools.cycle(('.',
 'o',
 'v',
 '^',
 '<',
 '>',
 '1',
 '2',
 '3',
 '4',
 '8',
 's',
 'p',
 '*',
 'h',
 'H',
 '+',
 'x',
 'D',
 'd',
 '|',
 'P',
 'X',
 0,
 1,
 2,
 3,
 4,
 5,
 6,
 7,
 8,
 9,
 10,
 11,
))
def get_files_with_path(folder):
    print(folder)
    return [os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]
dir = 'e:/porno/tesis 3/tesisfisica/criostato/Archivos/X5/rampas/'
rampas = get_files_with_path(dir)
#filename = 'X5-711-a.csv'
marker = marker_l()
for filename in rampas:
    try:
        T, s, h, v1, i1, r1, v2, i2, r2 = np.genfromtxt(filename, usecols=(1,2,3,4,5,6,7,8,9), delimiter=',', unpack=True, skip_header=1)
    except:
        t, T, s, h, r1, r2 = np.genfromtxt(filename, delimiter=',', unpack=True, skip_header=1)
    if filename == 'e:/porno/tesis 3/tesisfisica/criostato/Archivos/X5/rampas/RampaRdeT711.csv':
        r1 = r1[:]
        continue
    elif filename == 'e:/porno/tesis 3/tesisfisica/criostato/Archivos/X5/rampas/RampaRdeT811.csv':
        r1 = r1[:1512]
        T = T[:1512]
        continue
    elif filename == 'e:/porno/tesis 3/tesisfisica/criostato/Archivos/X5/rampas/RampaRdeT1212.csv':
        r1 = r1[:1850]
        T = T[:1850]
        filename = 'e:/porno/tesis 3/tesisfisica/criostato/Archivos/X5/rampas/RampaRdeT1212 I=1 mA.csv'
        # continue
    elif filename == 'e:/porno/tesis 3/tesisfisica/criostato/Archivos/X5/rampas/RampaRdeT1212 I=10 mA.csv':
        r1 = r1[1850:]
        T = T[1850:]
        # continue
    elif filename == 'e:/porno/tesis 3/tesisfisica/criostato/Archivos/X5/rampas/RampaRdeT1312 I=0,1 mA.csv':
        pass
        # continue
    elif filename == 'e:/porno/tesis 3/tesisfisica/criostato/Archivos/X5/rampas/RampaRdeT1712b.csv':
        # pass
        continue
    elif filename == 'e:/porno/tesis 3/tesisfisica/criostato/Archivos/X5/rampas/RampaRdeT1812.csv':
        # pass
        continue
    mk = next(marker)
    plt.scatter(T, r1/41, marker=mk, s=10, label=f'{filename.split("/")[-1].split("T")[-1].split("b")[0].split(".")[0].split(' ')[-2]} mA') 
    #dividir por 41 la r  
# xdeox = np.array([1, 10, 40, 50, 60, 70, 80, 90, 100, 105, 110, 120, 135, 150, 200, 250, 300])
# ydeox = np.array([4e-2, 3.8e-2, 3.8e-2, 4e-2, 4.2e-2, 6e-2, 1e-1, 1.3e-1, 1.47e-1, 1.5e-1, 1.47e-1, 1.41e-1, 1.2e-1, 1.1e-1, 9e-2, 8e-2, 7.5e-2])
# mk = next(marker)
# plt.plot(xdeox, ydeox, marker=mk, label='Qi $\delta$ ~ 0.04 $\\rho_c$ ', color='black')
# xdeox = np.array([1, 10, 40, 50, 60, 70, 100, 130, 160, 200, 250, 300])
# ydeox = np.array([1e-5, 2e-5, 1e-3, 2e-3, 3e-3, 4e-3, 2e-2, 3e-2, 2.6e-2, 1.6e-2, 1e-2, 0.8e-2])
# mk = next(marker)
# plt.plot(xdeox, ydeox, marker=mk, label='Qi $\delta$ ~ 0.04 $\\rho_a$ I=0.05mA', color='blue')
# plt.yscale('symlog')
# plt.yticks([0e-2, 2e-2, 4e-2, 6e-2, 8e-2, 1e-1, 1.2e-1, 1.4e-1, 1.6e-1, 1.8e-1, 2e-1])
plt.xlim(10,100)
plt.xlabel('T (K)')
plt.ylabel('$\\rho$ ($\Omega$ cm)')
# plt.suptitle(f'Resistividad 4 terminales, I = 1 mA')
plt.legend()
plt.grid()
plt.show()