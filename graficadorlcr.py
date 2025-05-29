# -*- coding: utf-8 -*-
"""
Created on Wed Jul  3 20:57:00 2024

@author: Administrator
"""
################# IMPORTS #########################
#%%
import sys
from functools import partial
from PyQt5.Qt import *
from PyQt5 import QtGui
import scipy.signal
import numpy as np
from numpy import diff
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter, freqz
import os
import glob
from statsmodels.nonparametric.smoothers_lowess import lowess
import itertools
from scipy.interpolate import lagrange
from scipy.optimize import newton
from scipy.optimize import curve_fit
from matplotlib.colors import Normalize
from os.path import abspath, dirname
os.chdir(dirname(abspath(__file__)))
window_size=31 
#%%
################# BOTON ###########################
#%%
class PushButton(QPushButton):
    def __init__(self, text, parent=None):
        super(PushButton, self).__init__(text, parent)

        self.setText(text)
        self.setMinimumSize(QSize(900, 250))
        self.setMaximumSize(QSize(900, 250))
        

class MyWindow(QMainWindow):
#%%
    ############## INICIO LOGICA VENTANA  #################################
#%%
    def __init__(self):
        super(MyWindow, self).__init__()
        self.setWindowTitle('Graficador')
        self.setFixedWidth(600)
        self.rows = 6
        self.columns = 6
        self.memoria = np.loadtxt('tempfilelcr.txt', dtype=str)
        self.memoria = self.memoria.tolist()
        self.setWindowIcon(QtGui.QIcon('snowflake.png'))
        os.chdir(dirname(abspath(__file__)))
        self.home = os.getcwd()
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self.main_layout = QVBoxLayout(centralWidget)
        
        self.label = QLabel(self, alignment=Qt.AlignRight)
        self.label.setFont(QFont("Times", 12, QFont.Bold))
            
        self.layout = QGridLayout() 
        self.main_layout.addLayout(self.layout)
        self.main_layout.addWidget(self.label)

#%% Logica de graficador de IVs
        _list = ['ω vs |z|, θ', 'ω v Re(Z),-Im(Z) (gol)', 'Re(Z) vs -Im(Z)', 'V bias vs Max(re/img z)', 'ω vs Re(Z),-Im(Z)']
        self.vbias = 0
        len_list = len(_list)-1
        self.seleccion = 'rdy'
        self.fileName = []
        try:
            self.texto_archivos = self.memoria.split('¡')
        except Exception as e:
            print(e,'77')
            self.texto_archivos = ''
            self.fileName = []
        try:
            for i in self.texto_archivos:
                    index = i.find(r'/IVs')
                    i = i[index:]
                    self.fileName.append(i)
        except Exception as e:
            print(e,'85')
            self.fileName = [str(self.texto_archivos)]
        print(self.fileName,'87')
        i = 0
        for row in range(3): 
           for column in range(2):
                button = PushButton(f'{_list[i]}', self)
                button.clicked.connect(partial(self.onClicked, _list[i]))
                button.setCheckable(True)
                self.layout.addWidget(button, row+1, column)
                button.setFixedSize(130, 50)  
                i += 1
                if i == len_list+1: break
            
        eis = PushButton('EIS file', self)
        eis.clicked.connect(partial(self.eiser))
        self.layout.addWidget(eis, 3, 1)
        eis.setFixedSize(130, 50)  
            
        graph = PushButton('Graficar', self)
        graph.clicked.connect(partial(self.graficar))
        self.layout.addWidget(graph, 4, 0)
        graph.setFixedSize(130, 50)  
        
        file = PushButton('File', self)
        file.clicked.connect(partial(self.open_file_explorer))
        self.layout.addWidget(file, 4, 1)
        file.setFixedSize(130, 50)  
        file.setCheckable(True)

        closer = PushButton('Cerrar', self)
        closer.clicked.connect(partial(self.closer))
        self.layout.addWidget(closer, 4, 2)
        closer.setFixedSize(130, 50)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)  # Ensures that the widget inside the scroll area can resize
        self.main_layout.addWidget(scroll_area)
        scroll_content = QWidget()
        scroll_area.setWidget(scroll_content)
        scroll_layout = QVBoxLayout(scroll_content)
        self.archivaje = QLabel(self)
        self.archivaje.setWordWrap(True)  # Enable word wrap for the label
        scroll_layout.addWidget(self.archivaje)
        self.archivaje.setText('Archivos:'+ str(self.fileName))
            
    def N_esimo(self, lst, n):
            # 'list ==> list, return every nth element in lst for n > 0'
            return lst[::n]

    def Z_RLC_s(self, omega2, R2, L2, C2):
        return (R2 + 1j*(omega2*L2-1/(omega2*C2)))

    def Z_RC_s(self, omega2, R2, C2):
        return (R2 - 1j/(omega2*C2))

    def Z_RC_p(self, omega2, R2, C2):
        return (R2*(- 1j/(omega2*C2))/(R2-1j/(omega2*C2)))


    def Zteo1(self, omega2, R1, C1, R2, C2, R3):
        ZZteo1=Z_RC_p(omega2, R1, C1) + Z_RC_p(omega2, R2, C2) + R3
        return ZZteo1

    def onClicked(self, i):
        if self.seleccion=='rdy':
            self.seleccion=[]
        if i not in self.seleccion:
            self.seleccion.append(i)
        elif i in self.seleccion:
            self.seleccion.remove(i)

    def open_file_explorer(self):
        options = QFileDialog.Options()
        self.fileName, _ = QFileDialog.getOpenFileNames(self, "Open File", "", "All Files (*)", options=options)
        self.texto_archivos = ''
        for i in np.arange(0,len(self.fileName)):
            print(self.fileName[i])
            index = self.fileName[i].find(r'/IVs')
            archtemp = self.fileName[i][index:]
            print(self.fileName[i][index:])
            self.texto_archivos = self.texto_archivos + archtemp + '¡'
            self.fileName[i] = self.fileName[i][index:]
        self.archivaje.setText(f'<html>Archivos:{self.texto_archivos}.</html>')
        np.savetxt('tempfilelcr.txt', [self.texto_archivos[-1]], fmt='%s')

    def toggle(self, boton):
        if self.boton.isChecked():
            self.boton.setStyleSheet("background-color: #4CAF50; color: white;")  # Set style when pressed
        else:
            self.toggle_button.setStyleSheet("")

    def closer(self):
        plt.close('all')

    def eiser(self):
        for archivos in self.fileName:
            path = self.home
            archivo_actual = path+archivos
            print(archivo_actual)
            data = np.genfromtxt(archivo_actual, delimiter=',', skip_header=1, unpack=True)
            f = data[0] #frecuencia
            zreal = data[1] #lectura promedio A (Z real)
            SD_A = data[2] #sigma A
            zimag = -data[3] #lectura promedio B (Z img)
            SD_B = data[4] #sigma B
            Amp = data[5] #amplitud
            index = archivo_actual.find('IVs')
            archivo_actual = archivo_actual[index:]
            filename = str(archivo_actual)
            filename_i = filename.find(r'/Off')
            filename2 = path+r'/'+filename[:filename_i]
            print(filename[:filename_i])
            print(filename2)
            output = open(str(filename2)+r'/'+str(filename.split('_')[-2])+'mV_eis.', 'w')
            output.write(str(len(f)) + '\n' )
            for i in np.arange(len(f)):
                output.write(f'{zreal[i]} {zimag[i]} {f[i]}\n')
            output.close()
            os.chdir(self.home+r'/IVs')
#%% Logica graficador de IVS

    def graficar(self):
        for i in self.fileName:
            try:
                print(os.getcwd())
                archivo_actual = os.getcwd()+i
                print(archivo_actual)
                data = np.genfromtxt(archivo_actual, delimiter=',', skip_header=1, unpack=True)
            except Exception as e:
                print(e)
                continue
            f = data[0] #frecuencia
            zreal = data[1] #lectura promedio A (Z real)
            SD_A = data[2] #sigma A
            zimag = data[3] #lectura promedio B (Z img)
            SD_B = data[4] #sigma B
            Amp = data[5] #amplitud
            try:
                vbias = float(i.split('/')[-1].split('_')[-2])
                T = float(i.split('/')[-2].split('_')[-3])
            except Exception as e:
                print(e)
                continue
            zrealgol = zreal
            zimaggol = zimag
            z = zreal +1j*zimag
            zmod = np.abs(z)
            zmodgol = zmod
            omega = 2*np.pi*f
            fase = 180/np.pi*np.angle(z)
            fasegol = fase
            if 'ω vs |z|, θ' in self.seleccion:
                plt.figure()
                plt.subplot(1, 2, 1)
                plt.suptitle(f'$V_{'dc'}$ = {vbias} mV T={T} K')
                plt.scatter(omega, zmodgol)
                plt.xlabel(r'$\omega$ [rad/s]')
                plt.ylabel(r'$|Z_{eq}| ~[\Omega]$')
                plt.xscale('log')
                plt.legend(title='$V_{bias}$ (mV)')
                plt.grid()
                
                plt.subplot(1, 2, 2)
                plt.scatter(omega, fasegol)
                plt.xlabel(r'$\omega$ [rad/s]')
                plt.ylabel(r'Phase [deg]')
                plt.xscale('log')
                plt.legend(title='$V_{bias}$ (mV)')
                plt.grid()
                plt.tight_layout()
                plt.show()
                
            if 'ω v Re(Z),-Im(Z) (gol)' in self.seleccion:
                plt.figure()
                plt.subplot(1, 2, 1)
                plt.suptitle(f'$V_{'dc'}$ = {vbias} mV T={T} K')
                plt.scatter(omega, zrealgol)
                plt.xlabel(r'$\omega$ [rad/s]')
                plt.ylabel(r'R [$\Omega$]')
                plt.xscale('log')
                plt.legend(title='$V_{bias}$ (mV)')
                plt.grid()
                    
                plt.subplot(1, 2, 2)
                plt.scatter(omega, zimaggol)
                plt.suptitle(f'$V_{'dc'}$ = {vbias} mV T={T} K')
                plt.xlabel(r'$\omega$ [rad/s]')
                plt.ylabel(r'X [$\Omega$]')
                plt.xscale('log')
                plt.legend(title='$V_{bias}$ (mV)')
                plt.grid()
                plt.tight_layout()
                plt.show()
                
            if 'Re(Z) vs -Im(Z)' in self.seleccion:
                plt.figure()
                plt.scatter(zrealgol, -zimaggol)
                plt.suptitle(f'$V_{'dc'}$ = {vbias} mV T={T} K')
                plt.xlabel(r'Z$^{´}$ [$\Omega$]')
                plt.ylabel(r'-Z$^{´´}$ [$\Omega$]')
                plt.legend(title='T (K)')
                plt.grid()
                plt.tight_layout()
                plt.show()
                
            if 'V bias vs Max(re/img z)' in self.seleccion:
                plt.figure()
                plt.subplot(1, 2, 1)
                plt.suptitle(f'$V_{'dc'}$ = {vbias} mV T={T} K')
                plt.scatter(vbias, np.isfinite(zreal).max(), linestyle='dashed', color='blue',  linewidth=2)
                plt.xlabel(r'$V_{bias}$ [V]')
                plt.ylabel(r'Z$^{´}$ [$\Omega$]')
                plt.grid()
                plt.legend(title='T (K)')
                    
                plt.subplot(1, 2, 2)
                plt.suptitle(f'$V_{'dc'}$ = {vbias} mV T={T} K')
                plt.scatter(vbias, np.isfinite(zimag).max(), linestyle='dashed', color='red',  linewidth=2)
                plt.xlabel(r'$V_{bias}$ [V]')
                plt.ylabel(r'-Z$^{´´}$ [$\Omega$]')
                plt.legend(title='T (K)')
                plt.grid()
                plt.tight_layout()
                plt.show()
            if 'ω vs Re(Z),-Im(Z)' in self.seleccion:
                plt.figure()
                plt.subplot(1, 2, 1)
                plt.suptitle(f'$V_{'dc'}$ = {vbias} mV T={T} K')
                plt.scatter(omega, zreal)
                plt.xlabel(r'$\omega$ [rad/s]')
                plt.ylabel(r'R [$\Omega$]')
                plt.xscale('log')
                plt.legend(title='$V_{bias}$ (mV)')
                plt.grid()
                    
                plt.subplot(1, 2, 2)
                plt.suptitle(f'$V_{'dc'}$ = {vbias} mV T={T} K')
                plt.scatter(omega, zimag)
                plt.xlabel(r'$\omega$ [rad/s]')
                plt.ylabel(r'X [$\Omega$]')
                plt.xscale('log')
                plt.legend(title='$V_{bias}$ (mV)')
                plt.grid()
                plt.tight_layout()
                plt.show()

###################### FIN LOGICA GRAF #########################
#%% Codigo de pyqt5 para arrancar
if __name__ == '__main__':
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance() 
    w = MyWindow()
    w.show()
    sys.exit(app.exec_())