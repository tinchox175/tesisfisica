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
from PyQt5.Qt import QHBoxLayout, QApplication, QFont, QSize, QScrollArea, QMenu, QAction, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QGridLayout, QLineEdit, QFileDialog
from PyQt5 import QtGui
from PyQt5.Qt import Qt
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
from matplotlib.ticker import StrMethodFormatter
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
        # try:
        self.memoria = np.loadtxt('tempfile.txt', delimiter='@',unpack=True, dtype='str')
        self.setWindowTitle('Graficador')
        self.setFixedWidth(900)
        self.rows = 6
        self.columns = 6
        self.setWindowIcon(QtGui.QIcon('snowflake.png'))
        
        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        self.main_layout = QVBoxLayout(centralWidget)
        
        self.label = QLabel(self, alignment=Qt.AlignRight)
        self.label.setFont(QFont("Times", 12, QFont.Bold))
            
        self.layout = QGridLayout() 
        self.main_layout.addLayout(self.layout)
        self.main_layout.addWidget(self.label)
#%% Ajustador de IV
        self.modo_g = 'no_t'
        self.var_sclc_p = 'si'
        self.var_fit = 'no'
        self.var_man = 'no'
        
        sclcp = PushButton('SCLC-P', self)
        sclcp.clicked.connect(partial(self.sclc_p))
        self.layout.addWidget(sclcp, 0, 4)
        sclcp.setFixedSize(130, 50)
        sclcp.setCheckable(True)
        
        residuos = PushButton('Residuos', self)
        residuos.clicked.connect(partial(self.residuos))
        residuos.setCheckable(True)
        self.layout.addWidget(residuos, 0, 5)
        residuos.setFixedSize(130, 50)  
        
        residuos = PushButton('Residuos', self)
        residuos.clicked.connect(partial(self.residuos))
        self.layout.addWidget(residuos, 0, 6)
        residuos.setFixedSize(130, 50)  
        
        fit = PushButton('Ajustar', self)
        fit.clicked.connect(partial(self.fit))
        self.layout.addWidget(fit, 1, 4)
        fit.setFixedSize(130, 50)
        fit.setCheckable(True)
        
        lim_fit = QLineEdit(self)
        lim_fit.setPlaceholderText(self.memoria[1])
        self.layout.addWidget(lim_fit)
        lim_fit.textChanged.connect(self.update_lim_fit)
        
        p0_fit = QLineEdit(self)
        p0_fit.setPlaceholderText(self.memoria[2])
        self.layout.addWidget(p0_fit)
        p0_fit.textChanged.connect(self.update_p0_fit)
        
        manual = PushButton('Manual', self)
        manual.clicked.connect(partial(self.manual))
        self.layout.addWidget(manual, 2, 4)
        manual.setFixedSize(130, 50)
        manual.setCheckable(True)
        
        self.sign = PushButton('Signo (Todo)', self)
        self.layout.addWidget(self.sign, 3, 5)
        self.sign.setFixedSize(130, 50)
        self.menu = QMenu(self)
        action1 = QAction('Todos', self)
        action2 = QAction('Positivos', self)
        action3 = QAction('Negativos', self)
        action1.triggered.connect(partial(self.sgn, 'todo'))
        action2.triggered.connect(partial(self.sgn, 'pos'))
        action3.triggered.connect(partial(self.sgn, 'neg'))    
        self.menu.addAction(action1)
        self.menu.addAction(action2)
        self.menu.addAction(action3)
        self.sign.setMenu(self.menu)
        
        ponbus = PushButton('Buscador', self)
        ponbus.clicked.connect(partial(self.ponbuscador))
        self.layout.addWidget(ponbus, 3, 4)
        ponbus.setFixedSize(130, 50)
        ponbus.setCheckable(True)
        
        lim_man = QLineEdit(self)
        lim_man.setPlaceholderText(self.memoria[3])
        self.layout.addWidget(lim_man, 2, 5)
        lim_man.textChanged.connect(self.update_lim_man)
        
        p_man = QLineEdit(self)
        p_man.setPlaceholderText(self.memoria[4])
        self.layout.addWidget(p_man, 2, 6)
        p_man.textChanged.connect(self.update_p_man)
        
        graph_g = PushButton('Graficar', self)
        graph_g.clicked.connect(partial(self.graficar_g))
        graph_g.clicked.connect(partial(self.multi_g))
        self.layout.addWidget(graph_g, 4, 4)
        graph_g.setFixedSize(130, 50)  
    
#%% Logica de graficador de IVs
        _list = ['I vs V', 'Log(I) vs V', 'Log(Ibias) vs V', 'Rinst', 'Rrem', 'γ vs V', 'γ vs √V', 'γ vs 1/V']
        len_list = len(_list)-1
        #pongo variables base y algunas de la memoria
        self.secondary_windows = []
        self.seleccion = 'rdy'
        self.var_res = 'no'
        self.modo = 'no_t'
        self.posneg = 'todo'
        self.channel = '1'
        self.filt = 'no'
        self.ponbus = 'no'

        self.texto_archivos = self.memoria[0].split('¡')
        self.p0fit = []
        self.p_manual = []
        self.lower = float(self.memoria[1].split(',')[0])
        self.upper = float(self.memoria[1].split(',')[1])
        for i in self.memoria[2].split(','):
            self.p0fit.append(float(i))
        self.manmin = float(self.memoria[3].split(',')[0])
        self.manmax = float(self.memoria[3].split(',')[1])
        for i in self.memoria[4].split(','):
            self.p_manual.append(float(i))
        self.fileName = []
        print(self.texto_archivos)
        try:
            if type(self.texto_archivos)!=list:
                index = self.texto_archivos.find(r'/IVs')
                self.texto_archivos = self.texto_archivos[index:]
                self.fileName = self.texto_archivos
                print(self.fileName)
            else:
                for i in self.texto_archivos:
                    index = i.find(r'/IVs')
                    i = i[index:]
                    self.fileName.append(i)
        except TypeError:
            self.fileName = [str(self.texto_archivos)]
        try:
            if 'criostato' in self.texto_archivos[0]:
                self.fileName = []
                if type(self.texto_archivos)!=list:
                    index = self.texto_archivos.find(r'/criostato')
                    self.texto_archivos = self.texto_archivos[index:]
                    self.fileName = self.texto_archivos
                    print(self.fileName)
                else:
                    for i in self.texto_archivos:
                        index = i.find(r'/criostato')
                        i = i[index:]
                        self.fileName.append(i)
        except TypeError:
            self.fileName = [str(self.texto_archivos)]
        
        i = 0
        for row in range(3): 
           for column in range(3):
                button = PushButton(f'{_list[i]}', self)
                button.clicked.connect(partial(self.onClicked, _list[i]))
                button.setCheckable(True)
                self.layout.addWidget(button, row+1, column)
                button.setFixedSize(130, 50)  
                i += 1
                if i == len_list+1: break
        
        button = PushButton(f'Panorama', self)
        button.clicked.connect(partial(self.onClicked, 'Panorama'))
        button.setCheckable(True)
        self.layout.addWidget(button, 0, 1)
        button.setFixedSize(130, 50)  

        button = PushButton(f'Filtrado', self)
        button.clicked.connect(partial(self.filter))
        button.setCheckable(True)
        self.layout.addWidget(button, 3, 2)
        button.setFixedSize(130, 50)  
        
        graph = PushButton('Graficar', self)
        graph.clicked.connect(partial(self.graficar))
        self.layout.addWidget(graph, 4, 0)
        graph.setFixedSize(130, 50)  
        
        file = PushButton('File', self)
        file.clicked.connect(partial(self.open_file_explorer))
        self.layout.addWidget(file, 4, 1)
        file.setFixedSize(130, 50)  
        
        closer = PushButton('Cerrar', self)
        closer.clicked.connect(partial(self.closer))
        self.layout.addWidget(closer, 4, 5)
        closer.setFixedSize(130, 50)

        self.chnl = PushButton('Canal 1', self)
        self.layout.addWidget(self.chnl, 4, 2)
        self.chnl.setFixedSize(130, 50)
        self.menu = QMenu(self)

        caction1 = QAction('1', self)
        caction2 = QAction('2', self)
        caction3 = QAction('Criostato', self)
        caction1.triggered.connect(partial(self.selcan, '1'))
        caction2.triggered.connect(partial(self.selcan, '2'))
        caction3.triggered.connect(partial(self.selcan, 'Criostato'))
        self.menu.addAction(caction1)
        self.menu.addAction(caction2)
        self.menu.addAction(caction3)
        self.chnl.setMenu(self.menu)

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
                
    def update_lim_fit(self, text):
    # Update variable
        if len(text.split(',')) > 1:
            try:
                self.lower = int(text.split(',')[0])
                self.upper = int(text.split(',')[1])
                print(self.lower, self.upper)
            except ValueError:
                pass
        try:
            np.savetxt('tempfile.txt', [self.texto_archivos[-1]+r'@'+str(self.lower)+r','+str(self.upper)+r'@'+str(self.p0fit[0])+','+str(self.p0fit[1])+'@'+str(self.manmin)+','+str(self.manmax)+'@'+str(self.p_manual[0])+','+str(self.p_manual[1])], delimiter=',', fmt='%s')
        except:
            try:
                print([self.texto_archivos[-1]+r'@'+str(self.lower)+r','+str(self.upper)+r'@'+str(self.p0fit[0])+','+str(self.p0fit[1])+'@'+str(self.manmin)+','+str(self.manmax)+'@'+str(self.p_manual[0])+','+str(self.p_manual[1])], delimiter=',', fmt='%s')
            except (IndexError, TypeError) as e:
                pass
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
        try:
            np.savetxt('tempfile.txt', [self.texto_archivos[-1]+r'@'+str(self.lower)+r','+str(self.upper)+r'@'+str(self.p0fit[0])+','+str(self.p0fit[1])+'@'+str(self.manmin)+','+str(self.manmax)+'@'+str(self.p_manual[0])+','+str(self.p_manual[1])], delimiter=',', fmt='%s')
        except (IndexError, TypeError) as e:
            pass    
    def update_lim_man(self, text):
    # Update variable
        if len(text.split(',')) > 1:   
            try:
                self.manmin = int(text.split(',')[0])
                self.manmax = int(text.split(',')[1])
            except ValueError:
                pass
        print(self.manmin, self.manmax)
        print(self.texto_archivos)
        print(type(self.texto_archivos))
        np.savetxt('tempfile.txt', [self.texto_archivos[-1]+r'@'+str(self.lower)+r','+str(self.upper)+r'@'+str(self.p0fit[0])+','+str(self.p0fit[1])+'@'+str(self.manmin)+','+str(self.manmax)+'@'+str(self.p_manual[0])+','+str(self.p_manual[1])], delimiter=',', fmt='%s')
        try:
            np.savetxt('tempfile.txt', [self.texto_archivos[-1]+r'@'+str(self.lower)+r','+str(self.upper)+r'@'+str(self.p0fit[0])+','+str(self.p0fit[1])+'@'+str(self.manmin)+','+str(self.manmax)+'@'+str(self.p_manual[0])+','+str(self.p_manual[1])], delimiter=',', fmt='%s')
        except TypeError:
            try:
                print([self.texto_archivos[-1]+r'@'+str(self.lower)+r','+str(self.upper)+r'@'+str(self.p0fit[0])+','+str(self.p0fit[1])+'@'+str(self.manmin)+','+str(self.manmax)+'@'+str(self.p_manual[0])+','+str(self.p_manual[1])], delimiter=',', fmt='%s')
            except (IndexError, TypeError) as e:
                pass
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
        try:
            np.savetxt('tempfile.txt', [self.texto_archivos[-1]+r'@'+str(self.lower)+r','+str(self.upper)+r'@'+str(self.p0fit[0])+','+str(self.p0fit[1])+'@'+str(self.manmin)+','+str(self.manmax)+'@'+str(self.p_manual[0])+','+str(self.p_manual[1])], delimiter=',', fmt='%s')
        except (IndexError, TypeError) as e:
            pass
        
    def sgn(self, sg):
       if sg == 'todo':
           self.posneg = 'todo'
           self.sign.setText('Signo (Todo)')
       elif sg == 'pos':
           self.posneg = 'pos'
           self.sign.setText('Signo (+)')
       elif sg == 'neg':
           self.posneg = 'neg'
           self.sign.setText('Signo (-)')
    
    def ponbuscador(self):
        if self.ponbus=='si':
            self.ponbus = 'no'
        elif self.ponbus == 'no':
            self.ponbus = 'si'

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
    
    def residuos(self):
        if self.var_res=='si':
            self.var_res = 'no'
        elif self.var_res == 'no':
            self.var_res = 'si'
    
    def custom(self):
        if self.var_sclc_p=='si':
            self.var_sclc_p = 'no'
        elif self.var_sclc_p == 'no':
            self.var_sclc_p = 'si'
            
#%% Lógica graficar fits
    def multi_g(self):
        if type(self.fileName) == str:
            print(self.fileName+'str')
        elif type(self.fileName) == list:
            print(self.fileName, 'list')
    
    def filter(self):
        if self.filt=='no':
            self.filt='si'
        elif self.filt=='si':
            self.filt='no'

    def graficar_g(self):
        if str(type(self.fileName)) == '<class \'str\'>':
            archivo_actual = self.fileName
        elif str(type(self.fileName)) == '<class \'list\'>':
            archivo_actual = self.fileName[0]
        try:
            data = np.genfromtxt(os.getcwd()+archivo_actual, delimiter='\t', skip_header=1, unpack=True)
            data_t = np.genfromtxt(os.getcwd()+archivo_actual, delimiter='\t', dtype='str', unpack=True)
        except:
            print('No se pudo abrir el archivo')
            return
        if 'criostato' in archivo_actual:
                self.channel = 'crio'
        if '(K)' in data_t[1][0]:
            self.modo = 'si_t'
        elif '(K)' not in data_t[1][0]:
            self.modo = 'no_t'
        else:
            print('ups')
        if self.channel == '1':
            if self.modo == 'no_t':
                self.indoff = self.newoff(data[1])
                time = data[0][~np.isnan(data[0])] #tiempo
                ipul = data[1][~np.isnan(data[1])] #I pulso
                try:
                    vin1 = np.array(data[2][~np.isnan(data[2])])-(data[2][~np.isnan(data[2])][self.indoff[0]-1]+data[2][~np.isnan(data[2])][self.indoff[0]+1])/2 #V instant
                except IndexError:
                    vin1 = np.array(data[2][~np.isnan(data[2])])
                iin1 = data[3][~np.isnan(data[3])] #I instant
                rin1 = data[4][~np.isnan(data[4])] #R instant
                rre1 = data[5][~np.isnan(data[5])] #R remanente
                ibi1 = data[6][~np.isnan(data[6])] #I bias
                vbi1 = data[7][~np.isnan(data[7])] #V bias
                wpul = data[14][~np.isnan(data[14])] #ancho pulso
                peri = data[15][~np.isnan(data[15])] #periodo
                temperatura = 'T_amb'
            elif self.modo == 'si_t':
                self.indoff = self.newoff(data[2])
                time = data[0][~np.isnan(data[0])] #tiempo
                temp = data[1][~np.isnan(data[1])] #temp(k)
                ipul = data[2][~np.isnan(data[0])] #I pulso
                try:
                    vin1 = np.array(data[3][~np.isnan(data[3])])-(data[3][~np.isnan(data[3])][self.indoff[0]-1]+data[3][~np.isnan(data[3])][self.indoff[0]+1])/2 #V instant
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
        elif self.channel=='2':
                if self.modo == 'no_t':
                    iin1 = data[9][~np.isnan(data[9])] #I instant
                    self.indoff = self.newoff(iin1)
                    time = data[0][~np.isnan(data[0])] #tiempo
                    ipul = data[1][~np.isnan(data[1])] #I pulso
                    try:
                        vin1 = np.array(data[8][~np.isnan(data[9])])-np.array(data[9][~np.isnan(data[9])][self.indoff]) #V instant
                    except IndexError:
                        vin1 = np.array(data[8][~np.isnan(data[9])])
                    rin1 = data[10][~np.isnan(data[10])] #R instant
                    rre1 = data[11][~np.isnan(data[11])] #R remanente
                    ibi1 = data[12][~np.isnan(data[12])] #I bias
                    vbi1 = data[13][~np.isnan(data[13])] #V bias
                    wpul = data[14][~np.isnan(data[14])] #ancho pulso
                    peri = data[15][~np.isnan(data[15])] #periodo
                    temperatura = 'T_amb'
                elif self.modo == 'si_t':
                    self.indoff = self.newoff(data[2][~np.isnan(data[2])])
                    time = data[0][~np.isnan(data[0])] #tiempo
                    temp = data[1][~np.isnan(data[1])] #temp(k)
                    ipul = data[2][~np.isnan(data[2])] #I pulso
                    try:
                        vin1 = np.array(data[9][~np.isnan(data[9])])-np.array(data[9][~np.isnan(data[9])][self.indoff]) #V instant
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
        elif self.channel == 'crio':
                data = np.genfromtxt(os.getcwd()+archivo_actual, delimiter=',', skip_header=1, unpack=True)
                self.indoff = 0
                vin1 = np.array(data[0][~np.isnan(data[0])])
                iin1 = data[1][~np.isnan(data[1])]*1000 #I instant
                ibi1 = data[3][~np.isnan(data[3])]*1000 #I bias
                vbi1 = data[2][~np.isnan(data[0])] #V bias
                time = np.linspace(0,1,len(iin1)) #tiempo
                temperatura = archivo_actual.split('-')[-1]
                if 'nplc' in archivo_actual:
                    data = np.genfromtxt(os.getcwd()+archivo_actual, delimiter=',', skip_header=1, unpack=True)
                    self.indoff = 0
                    time = data[0][~np.isnan(data[0])]
                    vin1 = np.array(data[1][~np.isnan(data[1])])
                    iin1 = data[2][~np.isnan(data[2])]*1000 #I instant
                    vbi1 = data[3][~np.isnan(data[3])] #V bias
                    ibi1 = data[4][~np.isnan(data[4])]*1000 #I bias
                    temperatura = archivo_actual.split('-')[-2]
        if self.var_fit == 'si':
            def sclc_p(V, A, R):
                return A*np.abs(V)**2+V/R
            try:
                l = int(self.lower)
            except AttributeError:
                l = int(0)
                print('L es ' + l)
            try:
                u = int(self.upper)
            except AttributeError:
                u = int(-1)
            if self.posneg == 'pos':
                ix = self.busca_pos(vin1)
                print(ix)
                vin1, iin1 = [vin1[i] for i in ix], [iin1[i] for i in ix]
            elif self.posneg == 'neg':
                ix = self.busca_neg(vin1)
                print(ix)
                vin1, iin1 = [vin1[i] for i in ix], [iin1[i] for i in ix]
            elif self.posneg == 'todo':
                vin1, iin1 = vin1[l:u], iin1[l:u]
            try:
                initial_guess = self.p0fit
            except AttributeError:
                initial_guess = [0, 0]
            try:
                popt, pcov = curve_fit(sclc_p, vin1, iin1, sigma=np.full_like(iin1, 0.05e-1), absolute_sigma = True, p0=initial_guess, bounds=[[0,0],[1e40,100e3]])
            except (RuntimeError, ValueError) as err:
                print(err)
                return
            self.popt = popt
            self.pcov = pcov
            plt.figure(figsize=(20,10))
            mng_g = plt.get_current_fig_manager()
            mng_g.window.showMaximized()
            plt.scatter(vin1, np.abs(iin1), label='Data')
            plt.plot(vin1, np.abs(sclc_p(vin1, *popt)), label=f'Ajuste SCLC', c='orange')
            plt.title(f'Fit SCLC paralelo T={temperatura}')
            plt.xlabel('V')
            plt.ylabel('|I| (mA)')
            plt.ylim(np.min(iin1-np.abs(np.min(iin1))/10),np.max(iin1+np.abs(np.max(iin1))/10))
            plt.xlim(np.min(vin1-np.abs(np.min(vin1))/10),np.max(vin1+np.abs(np.max(vin1))/10))
            plt.grid(True)
            plt.legend()
            plt.show()
            self.w2 = VentanaAjustes(self.popt, self.pcov)
            self.w2.show()
            self.secondary_windows.append(self.w2)
            if self.var_res == 'si':
                plt.figure()
                plt.scatter(vin1, np.abs(iin1)-np.abs(sclc_p(vin1, *popt)), marker='o', label='Residuos', c='orange', zorder=10)
                plt.plot(vin1, (np.abs(iin1)-np.abs(sclc_p(vin1, *popt))), zorder=1)
                plt.grid(zorder=0)
                plt.xlabel('Voltaje [V]')
                plt.ylabel('|I| [mA]')
                plt.show()
            print(self.secondary_windows)
        if self.ponbus == 'si':
            try:
                plt.figure()
                indices = np.arange(len(vin1))
                sc = plt.scatter(vin1, iin1, s=1, c=time, cmap='viridis')
                cbar = plt.colorbar(sc, label='Tiempo (s)')
                for i in indices:
                    if iin1[i] > 0:
                        rgba_color = sc.cmap(sc.norm(time[i]))
                        plt.text(vin1[i], iin1[i], str(i), color=rgba_color)
                plt.xlabel("Voltaje [V]")
                plt.ylabel("Current [mA]")
                plt.xscale('log')
                plt.yscale('log')
                plt.grid(True)
                plt.tight_layout()
                plt.show()
            except:
                print('Negativos')
        if self.var_man == 'si':
            def sclc_p(V, A, R):
                V = [float(V[i]) for i in range(len(V))]
                V = np.array(V)
                return A*V**2+V/R
            try:
                A, R= self.p_manual
                R = R/1000
            except:
                A, R= [0,0]
            plt.figure(figsize=(20,10))
            mng_g2 = plt.get_current_fig_manager()
            mng_g2.window.showMaximized()
            self.manmin = int(self.manmin)
            self.manmax = int(self.manmax)
            if self.posneg == 'pos':
                ix = self.busca_pos(vin1)
                print(ix)
                vin1, iin1 = [vin1[i] for i in ix], [iin1[i] for i in ix]
            elif self.posneg == 'neg':
                ix = self.busca_neg(vin1)
                print(ix)
                vin1, iin1 = [vin1[i] for i in ix], [iin1[i] for i in ix]
            elif self.posneg == 'todo':
                vin1, iin1 = vin1[self.manmin:self.manmax], iin1[self.manmin:self.manmax]
            plt.scatter(vin1, iin1, label='Data',color='black')
            plt.plot(vin1, sclc_p(vin1, A, R), label=f'Ajuste manual', color='orange')
            plt.title('Fit SCLC paralelo')
            plt.xlabel('V')
            plt.ylabel('I (mA)')
            try:
                plt.ylim(np.min(iin1)-np.abs(np.min(iin1)/10),np.max(iin1)+np.max(iin1)/10)
                plt.xlim(np.min(vin1)-np.abs(np.min(vin1)/10),np.max(vin1)+np.max(vin1)/10)
            except:
                pass
            plt.grid(True)
            plt.legend()
            plt.show()
        return
    
    def busca_pos(self, vin1):
        return [index for index, value in enumerate(vin1) if value > 0]
                
    def busca_neg(self, vin1):
        return [index for index, value in enumerate(vin1) if value < 0]
    
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
            print(self.fileName[i])
            index = self.fileName[i].find(r'/IVs')
            archtemp = self.fileName[i][index:]
            print(self.fileName[i][index:])
            if self.fileName[i][index:]=='v':
                index = self.fileName[i].find(r'/criostato')
                archtemp = self.fileName[i][index:]
                self.channel = 'crio'
            self.texto_archivos = self.texto_archivos + archtemp + '¡'
            self.fileName[i] = self.fileName[i][index:]
        self.archivaje.setText(f'<html>Archivos:{self.texto_archivos}.</html>')
        np.savetxt('tempfile.txt', [self.texto_archivos[:-1]+r'@'+str(self.lower)+r','+str(self.upper)+r'@'+str(self.p0fit[0])+','+str(self.p0fit[1])+'@'+str(self.manmin)+','+str(self.manmax)+'@'+str(self.p_manual[0])+','+str(self.p_manual[1])], delimiter=',', fmt='%s')
    
    def closer(self):
        plt.close('all')
        for window in self.secondary_windows:
            window.close()
        self.secondary_windows.clear()
        
    def toggle(self, boton):
        if self.boton.isChecked():
            self.boton.setStyleSheet("background-color: #4CAF50; color: white;")  # Set style when pressed
        else:
            self.toggle_button.setStyleSheet("")


#%% Logica graficador de IVS
    def newoff(self,y):
        indices = np.argmin(np.abs(y))
        return indices

    def selcan(self, ch):
        if ch == '1':
            self.channel = '1'
            self.chnl.setText('Canal 1')
        elif ch == '2':
            self.channel = '2'
            self.chnl.setText('Canal 2')
        elif ch == 'Criostato':
            self.channel = 'crio'
            self.chnl.setText('Criostato')

    def graficar(self):
        print(self.fileName)
        for archivos in self.fileName:
            archivo_actual = archivos
            if 'criostato' in archivo_actual:
                self.channel = 'crio'
            data = np.genfromtxt(os.getcwd()+archivo_actual, delimiter='\t', skip_header=1, unpack=True)
            data_t = np.genfromtxt(os.getcwd()+archivo_actual, delimiter='\t', dtype='str', unpack=True)
            if '(K)' in data_t[1][0]:
                self.modo = 'si_t'
            elif '(K)' not in data_t[1][0]:
                self.modo = 'no_t'
            else:
                print('ups')
            if self.channel == '1':
                try:
                    if self.modo == 'no_t':
                        self.indoff = self.newoff(data[1][~np.isnan(data[1])])
                        time = data[0][~np.isnan(data[0])] #tiempo
                        ipul = data[1][~np.isnan(data[1])] #I pulso
                        try:
                            vin1 = np.array(data[2][~np.isnan(data[2])])-np.array(data[2][~np.isnan(data[2])][self.indoff]) #V instant
                        except IndexError:
                            vin1 = np.array(data[2][~np.isnan(data[2])])
                        iin1 = data[3][~np.isnan(data[3])] #I instant
                        rin1 = data[4][~np.isnan(data[4])] #R instant
                        rre1 = data[5][~np.isnan(data[5])] #R remanente
                        ibi1 = data[6][~np.isnan(data[6])] #I bias
                        vbi1 = data[7][~np.isnan(data[7])] #V bias
                        wpul = data[14][~np.isnan(data[14])] #ancho pulso
                        peri = data[15][~np.isnan(data[15])] #periodo
                        temperatura = 'T_amb'
                    elif self.modo == 'si_t':
                        self.indoff = self.newoff(data[2][~np.isnan(data[2])])
                        time = data[0][~np.isnan(data[0])] #tiempo
                        temp = data[1][~np.isnan(data[1])] #temp(k)
                        ipul = data[2][~np.isnan(data[2])] #I pulso
                        try:
                            vin1 = np.array(data[3][~np.isnan(data[3])])-np.array(data[3][~np.isnan(data[3])][self.indoff]) #V instant
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
            elif self.channel=='2':
                if self.modo == 'no_t':
                    iin1 = data[9][~np.isnan(data[9])] #I instant
                    self.indoff = self.newoff(iin1)
                    time = data[0][~np.isnan(data[0])] #tiempo
                    ipul = data[1][~np.isnan(data[1])] #I pulso
                    try:
                        vin1 = np.array(data[8][~np.isnan(data[8])])-np.array(data[8][~np.isnan(data[8])][self.indoff]) #V instant
                    except IndexError:
                        vin1 = np.array(data[8][~np.isnan(data[8])])
                    rin1 = data[10][~np.isnan(data[10])] #R instant
                    rre1 = data[11][~np.isnan(data[11])] #R remanente
                    ibi1 = data[12][~np.isnan(data[12])] #I bias
                    vbi1 = data[13][~np.isnan(data[13])] #V bias
                    wpul = data[14][~np.isnan(data[14])] #ancho pulso
                    peri = data[15][~np.isnan(data[15])] #periodo
                    temperatura = 'T_amb'
                elif self.modo == 'si_t':
                    self.indoff = self.newoff(data[2][~np.isnan(data[2])])
                    time = data[0][~np.isnan(data[0])] #tiempo
                    temp = data[1][~np.isnan(data[1])] #temp(k)
                    ipul = data[2][~np.isnan(data[2])] #I pulso
                    try:
                        vin1 = np.array(data[9][~np.isnan(data[9])])-np.array(data[9][~np.isnan(data[9])][self.indoff]) #V instant
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
            elif self.channel == 'crio':
                data = np.genfromtxt(os.getcwd()+archivo_actual, delimiter=',', skip_header=1, unpack=True)
                self.indoff = 0
                vin1 = np.array(data[0][~np.isnan(data[0])])
                iin1 = data[1][~np.isnan(data[1])]*1000 #I instant
                ibi1 = data[3][~np.isnan(data[3])]*1000 #I bias
                vbi1 = data[2][~np.isnan(data[0])] #V bias
                time = np.linspace(0,1,len(iin1)) #tiempo
                temperatura = archivos.split('-')[-1]
                if 'nplc' in archivo_actual:
                    data = np.genfromtxt(os.getcwd()+archivo_actual, delimiter=',', skip_header=1, unpack=True)
                    time = data[0][~np.isnan(data[0])] #tiempo
                    self.indoff = 0
                    vin1 = np.array(data[1][~np.isnan(data[1])])
                    iin1 = data[2][~np.isnan(data[2])]*1000 #I instant
                    ibi1 = data[4][~np.isnan(data[4])]*1000 #I bias
                    vbi1 = data[3][~np.isnan(data[3])] #V bias
                    time = np.linspace(0,1,len(iin1)) #tiempo
                    temperatura = archivos.split('-')[-1]
            try:
                iin1gol = iin1
                vin1gol = vin1
                ibi1gol = ibi1
                vbi1gol = vbi1
                rre1calcgol = vbi1gol/ibi1gol*1000
                rin1calcgol = vin1gol/iin1gol*1000
            except Exception as err:
                print(err)
                continue
            with np.errstate(all='raise'):
                try:
                    gamma1gol = diff(np.log(np.abs(iin1gol)))/diff(np.log(np.abs(vin1gol))) #gamma
                except Exception as err:
                    print(err)
                    try:
                        gamma1gol = diff(np.log(np.abs(iin1gol)+0.01))/diff(np.log(np.abs(vin1gol)+0.01)) #gamma savgol
                    except:
                        gamma1gol = np.full_like(vin1gol[0:-1], 100)
                        print('No hay gamma')
            if self.filt == 'si':
                try:
                    vin1gol = scipy.signal.savgol_filter(vin1, window_size, 3)
                    iin1gol = scipy.signal.savgol_filter(iin1, window_size, 3)
                    ibi1gol = scipy.signal.savgol_filter(ibi1, window_size, 3)        # Ibias1 savgol
                    vbi1gol = scipy.signal.savgol_filter(vbi1, window_size, 3)        # Vbias1 savgol
                    rre1calcgol = scipy.signal.savgol_filter(vbi1gol/ibi1gol, window_size, 3) # Rrem1 savgol
                    rin1calcgol = scipy.signal.savgol_filter(vin1gol/iin1gol, window_size, 3) # Rin1 savgol
                except:
                    pass
                with np.errstate(all='raise'):
                    try:
                        gamma1gol = diff(np.log(np.abs(iin1gol)))/diff(np.log(np.abs(vin1gol))) #gamma savgol
                    except Exception as err:
                        print(err)
                        gamma1gol = diff(np.log(np.abs(iin1gol)+0.01))/diff(np.log(np.abs(vin1gol)+0.01)) #gamma savgol
                        print((np.abs(vin1gol)))
            try:
                if  'I vs V' in self.seleccion:
                    plt.figure(figsize=(4,3), dpi=150)
                    # graficamos I vs V
                    plt.plot(vin1gol, iin1gol, lw=4, c="#4A85F1")  # pastel blue
                    plt.axvline(0, color='black', linestyle='dashed', linewidth=0.5)
                    plt.axhline(0, color='black', linestyle='dashed', linewidth=0.5)
                    plt.ylabel('I (mA)')
                    plt.xlabel('V (V)')
                    plt.tight_layout()
                    # plt.title(f'|I| vs V T={temperatura}')
                    plt.grid()
                    plt.tight_layout()
                    plt.show()
                if 'Log(I) vs V' in self.seleccion:
                    plt.figure()
                    # graficamos la Log(abs(I)) vs V    
                    plt.scatter(vin1gol, np.log(np.abs(iin1gol)+0.001), c=time, cmap='cool', norm=Normalize())
                    plt.colorbar(label='Tiempo (s)')
                    plt.yscale('log')
                    plt.axvline(0, color='black', linestyle='dashed', linewidth=0.5)
                    plt.axhline(1, color='black', linestyle='dashed', linewidth=0.5)
                    plt.xlabel('V (V)')
                    plt.ylabel('I (A)')
                    plt.title(f'Log(I) vs V T={temperatura}')
                    plt.grid()
                    plt.tight_layout()
                    plt.show()
                if 'Log(Ibias) vs V' in self.seleccion:
                    plt.figure()
                    # graficamos Log(abs(Ibias)) vs V
                    plt.scatter(vin1gol, np.log(np.abs(ibi1gol)+0.001), c=time, cmap='cool', norm=Normalize())
                    plt.colorbar(label='Tiempo (s)')
                    plt.yscale('log')
                    plt.xlabel('V (V)')
                    plt.ylabel('I$_{bias}$ (A)')
                    plt.xlim(-max(vin1gol), max(vin1gol))
                    plt.title(f'Log(I_{'bias'}) vs V T={temperatura}')
                    plt.grid()
                    plt.tight_layout()
                    plt.show()
                if 'Rinst' in self.seleccion:
                    plt.figure()
                    plt.subplot(1, 2, 1)
                    # graficamos la Rinst vs V    
                    plt.scatter(vin1gol, rin1calcgol, c=time, cmap='cool', norm=Normalize())
                    plt.colorbar(label='Tiempo (s)')
                    plt.axvline(0, color='black', linestyle='dashed', linewidth=0.5)
                    plt.axhline(1, color='black', linestyle='dashed', linewidth=0.5)
                    plt.xlabel('Voltaje (V)')
                    plt.ylabel('R$_{inst}$ ($\Omega$)')
                    #plt.xlim(-2, 2)
                    plt.ylim(0, 1.1*(np.nanmax(rin1calcgol)))
                    plt.title('R$_{inst}$ vs V '+f'T={temperatura}')
                    plt.grid()
                    plt.tight_layout()
                    
                    plt.subplot(1, 2, 2)
                    # graficamos la Rinst vs I    
                    plt.scatter(iin1gol, rin1calcgol, c=time, cmap='cool', norm=Normalize())
                    plt.colorbar(label='Tiempo (s)')
                    plt.axvline(0, color='black', linestyle='dashed', linewidth=0.5)
                    plt.axhline(1, color='black', linestyle='dashed', linewidth=0.5)
                    plt.xlabel('I (A)')
                    plt.ylabel('R$_{inst}$ ($\Omega$)')
                    #plt.xlim(-2, 2)
                    plt.ylim(0, 1.1*(np.nanmax(rin1calcgol)))
                    plt.title('R$_{inst}$ vs I '+f' T={temperatura}')
                    plt.grid()
                    plt.tight_layout()
                    plt.show()
                if 'Rrem' in self.seleccion:
                    plt.figure()
                    plt.subplot(1,2,1)
                    # graficamos la Rrem vs V    
                    plt.scatter(vin1gol, rre1calcgol, c=time, cmap='cool', norm=Normalize())
                    plt.colorbar(label='Tiempo (s)')
                    plt.axvline(0, color='black', linestyle='dashed', linewidth=0.5)
                    plt.axhline(1, color='black', linestyle='dashed', linewidth=0.5)
                    plt.xlabel('Voltaje (V)')
                    plt.ylabel('R$_{rem}$ ($\Omega$)')
                    #plt.xlim(-2, 2)
                    plt.ylim(0, 1.1*(np.nanmax(rin1calcgol)))
                    plt.title('R$_{rem}$ vs V '+f'T={temperatura}')
                    plt.tight_layout()
                    plt.grid()
                    
                    plt.subplot(1,2,2)
                    # graficamos la Rrem vs I    
                    plt.scatter(iin1gol, rre1calcgol, c=time, cmap='cool', norm=Normalize())
                    plt.colorbar(label='Tiempo (s)')
                    plt.axvline(0, color='black', linestyle='dashed', linewidth=0.5)
                    plt.axhline(1, color='black', linestyle='dashed', linewidth=0.5)
                    plt.xlabel('I (A)')
                    plt.ylabel('R$_{rem}$ ($\Omega$)')
                    #plt.xlim(-2, 2)
                    plt.ylim(0, 1.1*(np.nanmax(rin1calcgol)))
                    plt.title('R$_{rem}$ vs I '+f'T={temperatura}')
                    plt.tight_layout()
                    plt.grid()
                    plt.show()
                if 'γ vs V' in self.seleccion:
                    plt.figure()
                    # graficamos la gamma vs V    
                    plt.scatter(vin1gol[0:-1], gamma1gol, c=time[0:-1], cmap='cool', norm=Normalize())
                    plt.colorbar(label='Tiempo (s)')
                    plt.axvline(0, color='black', linestyle='dashed', linewidth=0.5)
                    plt.axhline(1, color='black', linestyle='dashed', linewidth=0.5)
                    # Fijamos cuestions cosméticas del grafico: etiquetas, limites, etc.
                    plt.xlabel('Voltaje (V)')
                    plt.ylabel('$\gamma$')
                    #plt.xlim(-2, 2)
                    plt.ylim(0, 2.5)
                    plt.title('$\gamma$ vs V '+ f'T={temperatura}')
                    plt.grid()
                    plt.tight_layout()
                    plt.show()
                if 'γ vs √V' in self.seleccion:
                    plt.figure()
                    plt.scatter(np.sign(vin1[0:-1])*np.sqrt(np.abs(vin1[0:-1])), gamma1gol, c=time[0:-1], cmap='cool', norm=Normalize())
                    plt.colorbar(label='Tiempo (s)')
                    plt.axvline(0, color='black', linestyle='dashed', linewidth=0.5)
                    plt.axhline(1, color='black', linestyle='dashed', linewidth=0.5)
                    # Fijamos cuestions cosméticas del grafico: etiquetas, limites, etc.
                    plt.xlabel('V$^{1/2}$ (V$^{0.5}$)')
                    plt.ylabel('$\gamma$')
                    #plt.xlim(-2, 2)
                    plt.ylim(0, 2.5)
                    plt.title('$\gamma$ vs V$^{1/2}$ '+f'T={temperatura}')
                    plt.grid()
                    plt.tight_layout()
                    plt.show()
                if 'γ vs 1/V' in self.seleccion:
                    plt.figure()
                    plt.scatter(1/vin1[0:-1], gamma1gol, gamma1gol, c=time[0:-1], cmap='cool', norm=Normalize())
                    plt.colorbar(label='Tiempo (s)')
                    plt.axvline(0, color='black', linestyle='dashed', linewidth=0.5)
                    plt.axhline(1, color='black', linestyle='dashed', linewidth=0.5)
                    # Fijamos cuestions cosméticas del grafico: etiquetas, limites, etc.
                    plt.xlabel('1/V (1/V)')
                    plt.ylabel('$\gamma$')
                    plt.xlim(-10, 10)
                    plt.ylim(0, 2.5)
                    plt.title(f'$\gamma$ vs 1/V T={temperatura}')
                    plt.grid()
                    plt.tight_layout()
                    plt.show()
                if 'Panorama' in self.seleccion:
                    # Create figure
                    fig = plt.figure()
                    mng = plt.get_current_fig_manager()
                    mng.window.showMaximized()
                    fig.suptitle(f'T = {temperatura}')
                    # First subplot (top-left)
                    ax1 = plt.subplot2grid((2, 3), (0, 0))
                    sc1 = ax1.scatter(vin1gol, iin1gol, c=time, cmap='cool')
                    ax1.set_xlabel('Voltaje (V)')
                    ax1.set_ylabel('I (mA)')
                    ax1.set_title('I vs V')
                    plt.tight_layout()
                    # Second subplot (bottom-left)
                    ax2 = plt.subplot2grid((2, 3), (1, 0))
                    sc2 = ax2.scatter(vin1gol[0:-1], gamma1gol, c=time[0:-1], cmap='cool')
                    ax2.set_xlabel('Voltaje (V)')
                    ax2.set_ylim(0,3)
                    ax2.axvline(0, color='black', linestyle='dashed', linewidth=0.5)
                    ax2.axhline(1, color='black', linestyle='dashed', linewidth=0.5)
                    ax2.set_ylabel('γ')
                    ax2.set_title('γ vs V')
                    plt.tight_layout()
                    # Third subplot (top-right)
                    ax3 = plt.subplot2grid((2, 3), (0, 1), rowspan=2)
                    sc3 = ax3.scatter(vin1gol, rin1calcgol, c=time, cmap='cool')
                    ax3.set_ylim(np.nanmin(rin1calcgol)*0.98,np.nanmax(rin1calcgol)*1.02)
                    ax3.set_xlabel('Voltaje (V)')
                    ax3.set_ylabel('$R_{inst}$ (Ω)')
                    ax3.set_title('$R_{inst}$ vs V')
                    plt.tight_layout()
                    # Fourth subplot (bottom-right)
                    ax4 = plt.subplot2grid((2, 3), (0, 2), rowspan=2)
                    sc4 = ax4.scatter(vin1gol, rre1calcgol, c=time, cmap='cool')
                    ax4.set_ylim(np.nanmin(rre1calcgol)*0.98,np.nanmax(rre1calcgol)*1.02)
                    ax4.set_xlabel('Voltaje (V)')
                    ax4.set_ylabel('$R_{rem}$ (Ω)')
                    ax4.set_title('$R_{rem}$ vs V')
                    cbar4 = plt.colorbar(sc4, ax=ax4)
                    cbar4.set_label('Time (s)')
                    ax1.grid()
                    ax2.grid()
                    ax3.grid()
                    ax4.grid()
                    plt.tight_layout()
                    plt.tight_layout()
                    plt.show()
            except Exception as err:
                print(err)
            plt.tight_layout()
###################### FIN LOGICA GRAF #########################
#%%
class VentanaAjustes(QWidget):
    def __init__(self, popt, pcov):
        super().__init__()
        # Set up the secondary window
        self.setWindowTitle(' ')
        self.setGeometry(200, 200, 300, 200)
        self.setWindowIcon(QtGui.QIcon('snowflake.png'))
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        popt[1] = popt[1]
        errores = np.sqrt(np.diag(pcov))
        errores[1] = errores[1]
        # Create layout and widgets
        layout = QVBoxLayout(self)
        h_layout1 = QHBoxLayout()
        h_layout2 = QHBoxLayout()
        # h_layout3 = QHBoxLayout()
        
        self.copy_button1 = QPushButton('♻', self)
        self.copy_button1.setFixedSize(30, 30)  # Set the button to be square
        self.copy_button1.clicked.connect(partial(self.copy_to_clipboard1, popt, errores))
        
        self.copy_button2 = QPushButton('♻', self)
        self.copy_button2.setFixedSize(30, 30)  # Set the button to be square
        self.copy_button2.clicked.connect(partial(self.copy_to_clipboard2, popt, errores))

        # self.copy_button3 = QPushButton('♻', self)
        # self.copy_button3.setFixedSize(30, 30)  # Set the button to be square
        # self.copy_button3.clicked.connect(partial(self.copy_to_clipboard3, popt, errores))
        
        # Create non-editable text displays
        self.text_display0 = QLineEdit(r'A*V**n+V/R')
        self.text_display0.setReadOnly(True)
        layout.addWidget(self.text_display0)
        
        self.text_display1 = QLineEdit('A = '+str(np.format_float_scientific(popt[0],precision=3))+' ± '+str(np.format_float_scientific(errores[0], precision=3)))
        self.text_display1.setReadOnly(True)
        layout.addWidget(self.text_display1)
        
        self.text_display2 = QLineEdit('R = '+str(np.round(popt[1]*1000,3))+' ± '+str(np.round(errores[1]*1000,3))+' Ohm')
        self.text_display2.setReadOnly(True)

        # self.text_display3 = QLineEdit('n = '+str(np.round(popt[2],3))+' ± '+str(np.round(errores[2],3)))
        # self.text_display2.setReadOnly(True)
        
        h_layout1.addWidget(self.text_display1)
        h_layout1.addWidget(self.copy_button1)
        
        h_layout2.addWidget(self.text_display2)
        h_layout2.addWidget(self.copy_button2)

        # h_layout3.addWidget(self.text_display3)
        # h_layout3.addWidget(self.copy_button3)
        
        layout.addLayout(h_layout1)
        layout.addLayout(h_layout2)
        # layout.addLayout(h_layout3)
        
        self.setLayout(layout)
        
    def copy_to_clipboard1(self,popt,errores):
        text1 = str(np.format_float_scientific(popt[0],precision=3))
        text2 = str(np.format_float_scientific(errores[0],precision=3))
        text = text1 + '±' + text2
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        return
    
    def copy_to_clipboard2(self,popt, errores):
        text1 = str(np.round(popt[1]*1000,3))
        text2 = str(np.round(errores[1]*1000,3))
        text = text1 + '±' + text2
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        return
    
    # def copy_to_clipboard3(self,popt, errores):
    #     text1 = str(np.round(popt[2],3))
    #     text2 = str(np.round(errores[2],3))
    #     text = text1 + '±' + text2
    #     clipboard = QApplication.clipboard()
    #     clipboard.setText(text)
        return
#%% Codigo de pyqt5 para arrancar
if __name__ == '__main__':
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance() 
    w = MyWindow()
    w.show()
    sys.exit(app.exec_())