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
        self.setFixedWidth(900)
        self.rows = 6
        self.columns = 6
        
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self.main_layout = QVBoxLayout(centralWidget)
        
        self.label = QLabel(self, alignment=Qt.AlignRight)
        self.label.setFont(QFont("Times", 12, QFont.Bold))
            
        self.layout = QGridLayout() 
        self.main_layout.addLayout(self.layout)
        self.main_layout.addWidget(self.label)
#%% Ajustador de IV
        self.texto_archivos_g = ''
        self.var_sclc_p = 'si'
        self.var_fit = 'no'
        self.var_man = 'no'
        
        sclcp = PushButton('SCLC-P', self)
        sclcp.clicked.connect(partial(self.sclc_p))
        self.layout.addWidget(sclcp, 0, 4)
        sclcp.setFixedSize(130, 50)
        sclcp.setCheckable(True)
        
        otro = PushButton('Otro (X)', self)
        otro.clicked.connect(partial(self.otro))
        self.layout.addWidget(otro, 0, 5)
        otro.setFixedSize(130, 50)  
        
        custom = PushButton('Custom', self)
        otro.clicked.connect(partial(self.custom))
        self.layout.addWidget(custom, 0, 6)
        custom.setFixedSize(130, 50)
        
        fit = PushButton('Ajustar', self)
        fit.clicked.connect(partial(self.fit))
        self.layout.addWidget(fit, 1, 4)
        fit.setFixedSize(130, 50)
        fit.setCheckable(True)
        
        lim_fit = QLineEdit(self)
        lim_fit.setPlaceholderText('Mín,Máx')
        self.layout.addWidget(lim_fit)
        lim_fit.textChanged.connect(self.update_lim_fit)
        
        p0_fit = QLineEdit(self)
        p0_fit.setPlaceholderText('a0,b0,...')
        self.layout.addWidget(p0_fit)
        p0_fit.textChanged.connect(self.update_p0_fit)
        
        manual = PushButton('Manual', self)
        manual.clicked.connect(partial(self.manual))
        self.layout.addWidget(manual, 2, 4)
        manual.setFixedSize(130, 50)
        manual.setCheckable(True)
        
        lim_man = QLineEdit(self)
        lim_man.setPlaceholderText('Mínx,Máxx')
        self.layout.addWidget(lim_man)
        lim_man.textChanged.connect(self.update_lim_man)
        
        p_man = QLineEdit(self)
        p_man.setPlaceholderText('a,b,...')
        self.layout.addWidget(p_man)
        p_man.textChanged.connect(self.update_p_man)
        
        graph_g = PushButton('Graficar', self)
        graph_g.clicked.connect(partial(self.graficar_g))
        self.layout.addWidget(graph_g, 4, 4)
        graph_g.setFixedSize(130, 50)  
#%% Logica de graficador de IVs
        _list = ['ω vs |z|, θ', 'ω v Re(Z),-Im(Z) (gol)', 'Re(Z) vs -Im(Z)', 'V bias vs Max(re/img z)', 'ω vs Re(Z),-Im(Z)']
        len_list = len(_list)-1
        self.seleccion = 'rdy'
        self.texto_archivos = ''
        i = 0
        for row in range(3): 
           for column in range(3):
                print(len_list)
                print(i)
                print(_list[i])
                button = PushButton(f'{_list[i]}', self)
                button.clicked.connect(partial(self.onClicked, _list[i]))
                button.setCheckable(True)
                self.layout.addWidget(button, row+1, column)
                button.setFixedSize(130, 50)  
                i += 1
                if i == len_list+1: break
            
        graph = PushButton('Graficar', self)
        graph.clicked.connect(partial(self.graficar))
        self.layout.addWidget(graph, 4, 0)
        graph.setFixedSize(130, 50)  
        
        file = PushButton('File', self)
        file.clicked.connect(partial(self.open_file_explorer))
        self.layout.addWidget(file, 4, 1)
        file.setFixedSize(130, 50)  
        file.setCheckable(True)
    
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)  # Ensures that the widget inside the scroll area can resize
        self.main_layout.addWidget(scroll_area)
        scroll_content = QWidget()
        scroll_area.setWidget(scroll_content)
        scroll_layout = QVBoxLayout(scroll_content)
        self.archivaje = QLabel(self)
        self.archivaje.setWordWrap(True)  # Enable word wrap for the label
        scroll_layout.addWidget(self.archivaje)
        self.archivaje.setText('Archivos:')
                
    def update_lim_fit(self, text):
    # Update variable
        if len(text.split(',')) > 1:
            self.lower = int(text.split(',')[0])
            try:
                self.upper = int(text.split(',')[1])
            except ValueError:
                pass
        
    def update_p0_fit(self, text):
    # Update variable
        text = text.split(',')
        self.p0fit = []
        for i in text:
            try:
                self.p0fit.append(float(i))
            except ValueError:
                pass
            
    def update_lim_man(self, text):
    # Update variable
        if len(text.split(',')) > 1:   
            self.manmin = int(text.split(',')[0])
            try:
                self.manmax = int(text.split(',')[1])
            except ValueError:
                pass
        
    def update_p_man(self, text):
    # Update variable
        text = text.split(',')
        self.p_manual = []
        for i in text:
            try:
                self.p_manual.append(float(i))
            except ValueError:
                pass
            
    def manual(self):
        if self.var_man=='si':
            self.var_man = 'no'
        elif self.var_man == 'no':
            self.var_man = 'si'
    
    def fit(self):
        if self.var_fit=='si':
            self.var_fit = 'no'
        elif self.var_fit == 'no':
            self.var_fit = 'si'
    
    def sclc_p(self):
        if self.var_sclc_p=='si':
            self.var_sclc_p = 'no'
        elif self.var_sclc_p == 'no':
            self.var_sclc_p = 'si'
            
    def otro(self):
        if self.var_sclc_p=='si':
            self.var_sclc_p = 'no'
        elif self.var_sclc_p == 'no':
            self.var_sclc_p = 'si'
    
    def custom(self, ):
        if self.var_sclc_p=='si':
            self.var_sclc_p = 'no'
        elif self.var_sclc_p == 'no':
            self.var_sclc_p = 'si'
            
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
#%% Lógica graficar fits
    def graficar_g(self):
        archivo_actual = self.fileName[0]
        data = np.genfromtxt(archivo_actual, delimiter='\t', skip_header=1, unpack=True)
        self.indoff = self.newoff(data[1])
        time = data[0] #tiempo
        ipul = data[1] #I pulso
        try:
            vin1 = np.array(data[2])-(data[2][self.indoff[0]-1]+data[2][self.indoff[0]+1])/2 #V instant
        except IndexError:
            vin1 = np.array(data[2])
        iin1 = data[3] #I instant
        rin1 = data[4] #R instant
        rre1 = data[5] #R remanente
        ibi1 = data[6] #I bias
        vbi1 = data[7] #V bias
        wpul = data[14] #ancho pulso
        peri = data[15] #periodo
        plt.figure(figsize=(20,10))
        if self.var_fit == 'si':
            def sclc_p(V, A, R, c):
                return A*V**2+V/R

            l= self.lower
            u= self.upper

            # Step 3: Fit data to model using curve_fit
            initial_guess = self.p0fit  # Initial guess for the parameters [a, b, c]
            popt, pcov = curve_fit(sclc_p, vin1[l:u], iin1[l:u], p0=initial_guess)

            # Extracted parameters
            a_fit, b_fit, c_fit = popt

            plt.figure(1, figsize=(20,10))
            plt.subplot(1,3,2)
            plt.scatter(vin1[l:u], iin1[l:u], label='Data')
            plt.plot(vin1[l:u], sclc_p(vin1[l:u], *popt), label=f'A = {np.round(a_fit,3)}\n R = {np.round(b_fit,3)}')
            plt.title('Fit SCLC paralelo')
            plt.xlabel('V')
            plt.ylim(0,np.max(iin1))
            plt.xlim(0,np.max(vin1))
            plt.grid(True)
            plt.legend()
            plt.show()
            plt.subplot(1,3,1)
            plt.scatter(vin1[l:u], iin1[l:u], label='Data')
            plt.plot(vin1[l:u], sclc_p(vin1[l:u], *popt), label=f'A = {np.round(a_fit,3)}')
            plt.ylabel('I')
            plt.ylim(0,np.max(iin1))
            plt.xlim(0,1.5)
            plt.grid(True)
            plt.show()
            plt.subplot(1,3,3)
            plt.scatter(vin1[l:u], iin1[l:u], label='Data')
            plt.plot(vin1[l:u], sclc_p(vin1[l:u], *popt), label=f'A = {np.round(a_fit,3)}')
            plt.ylim(0,np.max(iin1))
            plt.xlim(1.5,np.max(vin1))
            plt.grid(True)
            plt.show()
        if self.var_man == 'si':
            for i in np.linspace(0.05,0.1,3):
                o, r, a = self.p_manual
                offset = o
                R = r
                A = a
                plt.subplot(1,3,2)
                if i == 0.05:
                    plt.scatter(vin1, iin1, label='Data',color='black')
                else:
                    plt.scatter(vin1, iin1, color='black')
                plt.plot(vin1, sclc_p(vin1, A, R, offset), label=f'A = {np.round(A,3)}\n R = {np.round(R,3)}')
                plt.title('Fit SCLC paralelo')
                plt.xlabel('V')
                plt.ylim(0,np.max(iin1))
                plt.xlim(self.manmin,self.manmax)
                plt.grid(True)
                plt.legend()
                plt.show()
                plt.subplot(1,3,1)
                plt.scatter(vin1, iin1, label='Data', color='black')
                plt.plot(vin1, sclc_p(vin1, A, R, offset), label=f'A = {np.round(A,3)}\n R = {np.round(R,3)}')
                plt.ylabel('I')
                plt.ylim(0,np.max(iin1))
                plt.xlim(self.manmin, (self.manmin+self.manmax)/2)
                plt.grid(True)
                plt.show()
                plt.subplot(1,3,3)
                plt.scatter(vin1, iin1, label='Data', color='black')
                plt.plot(vin1, sclc_p(vin1, A, R, offset), label=f'A = {np.round(A,3)}\n R = {np.round(R,3)}')
                plt.ylim(0,np.max(iin1))
                plt.xlim((self.manmin+self.manmax)/2,self.manmax)
                plt.grid(True)
                plt.show()

        # Print the fitted parameters
        print(f"Parámetros ajustados:\na = {a_fit}\nb = {b_fit}")
        return

    def onClicked(self, i):
        if self.seleccion=='rdy':
            self.seleccion=[]
        if i not in self.seleccion:
            self.seleccion.append(i)
        elif i in self.seleccion:
            self.seleccion.remove(i)

        print(self.seleccion)
    def open_file_explorer(self):
        options = QFileDialog.Options()
        self.fileName, _ = QFileDialog.getOpenFileNames(self, "Open File", "", "All Files (*)", options=options)
        self.texto_archivos = ''
        for i in np.arange(0,len(self.fileName)):
            self.texto_archivos = self.texto_archivos + self.fileName[i] + '<br>'
        self.archivaje.setText(f'<html>Archivos:{self.texto_archivos}.</html>')
        print(self.fileName)
        
    def toggle(self, boton):
        if self.boton.isChecked():
            self.boton.setStyleSheet("background-color: #4CAF50; color: white;")  # Set style when pressed
        else:
            self.toggle_button.setStyleSheet("")


#%% Logica graficador de IVS

    def graficar(self):
        for archivos in self.fileName:
            archivo_actual = archivos
            data = np.genfromtxt(archivo_actual, delimiter=',', skip_header=1, unpack=True)
            f = data[0] #frecuencia
            zreal = data[1] #lectura promedio A (Z real)
            SD_A = data[2] #sigma A
            zimag = data[4] #lectura promedio B (Z img)
            SD_B = data[5] #sigma B
            Amp = data[6] #amplitud
        zrealgol = scipy.signal.savgol_filter(zreal, window_size, 7)
        zimaggol = scipy.signal.savgol_filter(zimag, window_size, 7)
        z = zreal +1j*zimag[i]
        zmod = np.abs(z)
        zmodgol = scipy.signal.savgol_filter(zmod, window_size, 3)
        omega = 2*np.pi*f
        fase = 180/np.pi*np.angle(z)
        fasegol = scipy.signal.savgol_filter(fase, window_size, 3)
        if 'ω vs |z|, θ' in self.seleccion:
            plt.figure()
            plt.subplot(1, 2, 1)
            plt.plot(omega, zmodgol)
            plt.xlabel(r'$\omega$ [rad/s]')
            plt.ylabel(r'$|Z_{eq}| ~[\Omega]$')
            plt.xscale('log')
            plt.legend(title='$V_{bias}$ (mV)')

            plt.subplot(1, 2, 2)
            plt.plot(omega, fasegol)
            plt.xlabel(r'$\omega$ [rad/s]')
            plt.ylabel(r'Phase [deg]')
            plt.xscale('log')
            plt.legend(title='$V_{bias}$ (mV)')
            plt.show()
            
        if 'ω v Re(Z),-Im(Z) (gol)' in self.seleccion:
            plt.figure()
            plt.subplot(1, 2, 1)
            plt.plot(omega, zrealgol)
            plt.xlabel(r'$\omega$ [rad/s]')
            plt.ylabel(r'Z$^{´}$ [$\Omega$]')
            plt.xscale('log')
            plt.legend(title='$V_{bias}$ (mV)')
                
            plt.subplot(1, 2, 2)
            plt.plot(omega, -zimaggol)
            plt.xlabel(r'$\omega$ [rad/s]')
            plt.ylabel(r'-Z$^{´´}$ [$\Omega$]')
            plt.xscale('log')
            plt.legend(title='$V_{bias}$ (mV)')
            plt.show()
            
        if 'Re(Z) vs -Im(Z)' in self.seleccion:
            plt.figure()
            plt.plot(zrealgol, -zimaggol)
            plt.xlabel(r'Z$^{´}$ [$\Omega$]')
            plt.ylabel(r'-Z$^{´´}$ [$\Omega$]')
            plt.legend(title='T (K)')
            plt.show()
            
        if 'V bias vs Max(re/img z)' in self.seleccion:
            plt.figure()
            plt.subplot(1, 2, 1)
            plt.plot(vbias, np.isfinite(zreal).max(), linestyle='dashed', color='blue',  linewidth=2)
            plt.xlabel(r'$V_{bias}$ [V]')
            plt.ylabel(r'Z$^{´}$ [$\Omega$]')
            plt.legend(title='T (K)')
                
            plt.subplot(1, 2, 2)
            plt.plot(vbias, np.isfinite(zimag).max(), linestyle='dashed', color='red',  linewidth=2)
            plt.xlabel(r'$V_{bias}$ [V]')
            plt.ylabel(r'-Z$^{´´}$ [$\Omega$]')
            plt.legend(title='T (K)')

            plt.show()
        if 'ω vs Re(Z),-Im(Z)' in self.seleccion:
            plt.figure()
            plt.subplot(1, 2, 1)
            plt.plot(omega, zreal)
            plt.xlabel(r'$\omega$ [rad/s]')
            plt.ylabel(r'Z$^{´}$ [$\Omega$]')
            plt.xscale('log')
            plt.legend(title='$V_{bias}$ (mV)')

                
            plt.subplot(1, 2, 2)
            plt.plot(omega, -zimag)
            plt.xlabel(r'$\omega$ [rad/s]')
            plt.ylabel(r'-Z$^{´´}$ [$\Omega$]')
            plt.xscale('log')
            plt.legend(title='$V_{bias}$ (mV)')
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