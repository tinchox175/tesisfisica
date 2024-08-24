# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 03:59:59 2024

@author: Jerik
"""

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
import itertools
from scipy.interpolate import lagrange
from scipy.optimize import newton
from scipy.optimize import curve_fit
from matplotlib.colors import Normalize
import matplotlib.colors as mcolors
from os.path import abspath, dirname
colors = [
    "#FF0000", "#F71919", "#EF3232", "#E74B4B", "#DF6464",
    "#D77D7D", "#CF9696", "#C7AFAF", "#BFC8C8", "#B7E1E1",
    "#AFFAFF", "#9FF4FF", "#8FEEFF", "#7FE8FF", "#6FE2FF",
    "#5FD4FF", "#4FC6FF", "#3FB8FF", "#2FAAFA", "#1F9CF5",
    "#0F8EEF", "#007FEA"
]
norm = mcolors.Normalize(vmin=80, vmax=300)
cmap = mcolors.ListedColormap(colors)
temperaturas = np.concatenate(np.arange(80,300,10),295)
window_size=31 

datos = []
def newoff(y):
    indices = []
    for i in range(1, len(y)):
        if (y[i] >= 0 and y[i - 1] < 0) or (y[i] < 0 and y[i - 1] >= 0):
            indices.append(i)
    return indices
n = 0
fig, ax = plt.subplots()
for i in np.arange(80,290,10):
    data = np.loadtxt(str(i)+'.txt', unpack=True, delimiter='\t', skiprows=1)
    indoff = newoff(data[2])
    time = data[0][~np.isnan(data[0])] #tiempo
    temp = data[1][~np.isnan(data[1])] #temp(k)
    ipul = data[2][~np.isnan(data[0])] #I pulso
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
    vin1gol = scipy.signal.savgol_filter(vin1, window_size, 3)
    iin1gol = scipy.signal.savgol_filter(iin1, window_size, 3)
    ax.scatter(vin1gol, np.abs(iin1gol), color=colors[n])
    n += 1
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array(temperaturas)
cbar = plt.colorbar(sm, ax=ax)
cbar.set_ticks(temperaturas)  # Optional: Remove ticks if only gradient is neededplt.ylabel('|I| [mA]')
cbar.set_label('Temperatura [K]')  # Add label to the colorbar
ax.set_xlabel('V [V]')
ax.set_ylabel('|I| [mA]')
ax.set_yscale('log')
ax.grid()
plt.show()
