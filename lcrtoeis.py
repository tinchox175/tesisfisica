import numpy as np
import os

def get_files_with_path(folder):
    print(folder)
    return [os.path.join(folder, file) for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file))]
def list_folders_in_folder(folder_path):
    # List only directories in the given folder
    return [name for name in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, name))]

# Example usage
dirs = "C:/tesis git/tesisfisica/IVs/2011/ZdeW_1234_16-11-24/"
fil = list_folders_in_folder(dirs)
for j in fil:
    folder_path = dirs+j
    if folder_path.split('.')[-1] == 'png' or folder_path.split('.')[-1] == 'txt':
        pass
    files = get_files_with_path(folder_path)
    for archivos in files:
        path = os.getcwd()
        os.chdir(path)
        archivo_actual = archivos
        data = np.genfromtxt(archivo_actual, delimiter=',', skip_header=1, unpack=True)
        f = data[0] #frecuencia
        zreal = data[1] #lectura promedio A (Z real)
        SD_A = data[2] #sigma A
        zimag = data[3] #lectura promedio B (Z img)
        SD_B = data[4] #sigma B
        Amp = data[5] #amplitud
        index = archivo_actual.find('IVs')
        archivo_actual = archivo_actual[index:]
        filename = str(archivo_actual)
        filename = filename.split(r'/')
        print(filename)
        filename = filename[3]
        output = open(str(filename)+'_eis.txt', 'w')
        output.write(str(len(f)) + '\n' )
        for i in np.arange(len(f)):
            output.write(f'{zreal[i]} {-zimag[i]} {f[i]}\n')
        output.close()
        os.chdir(os.getcwd()+r'/IVs')