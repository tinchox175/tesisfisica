# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 15:59:41 2024

@author: Administrator
"""

import numpy as np
import matplotlib.pyplot as plt

t, a, r = np.genfromtxt('ajustesivneg.csv', delimiter=',', unpack=True, skip_header=1, dtype='str')
#%%
tt = []
for i in np.arange(0,len(t)):
    tt.append(np.float64(str(t[i])))
at = []
sat = []
rt = []
srt = []
for i in np.arange(0,len(a)):
    at.append(np.abs(np.float64(str(a[i]).split('Â±')[0])))
    rt.append(np.float64(str(r[i]).split('Â±')[0]))
    sat.append(np.float64(str(a[i]).split('Â±')[1]))
    srt.append(np.float64(str(r[i]).split('Â±')[1]))
plt.figure(figsize=(20,10))
plt.subplot(1,2,1)
plt.errorbar(t, at, yerr=sat,capsize=1, fmt='o-')
plt.grid()
plt.xlabel('Temperatura')
plt.ylabel('A')
plt.tight_layout()
plt.subplot(1,2,2)
plt.errorbar(t, rt, yerr=srt,capsize=1, fmt='o-')
plt.grid()
plt.xlabel('Temperatura')
plt.ylabel('R [k$\Omega$]')
plt.tight_layout()
mng = plt.get_current_fig_manager()
mng.window.showMaximized()
#%%
td = []
ta = []
for i in np.arange(0,len(t[1::2])):
    td.append(np.float64(str(t[1::2][i])))
for i in np.arange(0,len(t[0::2])):
    ta.append(np.float64(str(t[0::2][i])))
ad = []
sad = []
rd = []
srd = []
for i in np.arange(0,len(a[1::2])):
    ad.append(np.abs(np.float64(str(a[1::2][i]).split('Â±')[0])))
    rd.append(np.float64(str(r[1::2][i]).split('Â±')[0]))
    sad.append(np.float64(str(a[1::2][i]).split('Â±')[1]))
    srd.append(np.float64(str(r[1::2][i]).split('Â±')[1]))
aa = []
saa = []
ra = []
sra = []
for i in np.arange(0,len(a[0::2])):
    aa.append(np.abs(np.float64(str(a[0::2][i]).split('Â±')[0])))
    ra.append(np.float64(str(r[0::2][i]).split('Â±')[0]))
    saa.append(np.float64(str(a[0::2][i]).split('Â±')[1]))
    sra.append(np.float64(str(r[0::2][i]).split('Â±')[1]))
plt.figure(figsize=(20,10))
plt.subplot(1,2,1)
plt.errorbar(td, ad, yerr=sad,capsize=1, fmt='o-', label='Descenso')
plt.errorbar(ta, aa, yerr=saa,capsize=1, fmt='o-', label='Ascenso')
plt.xlabel('Temperatura')
plt.ylabel('A')
plt.grid()
plt.tight_layout()
plt.legend()
plt.subplot(1,2,2)
plt.errorbar(td, rd, yerr=srd,capsize=1, fmt='o-', label='Descenso')
plt.errorbar(ta, ra, yerr=sra,capsize=1, fmt='o-', label='Ascenso')
plt.grid()
plt.xlabel('Temperatura')
plt.ylabel('R [k$\Omega$]')
plt.tight_layout()
plt.legend()
mng = plt.get_current_fig_manager()
mng.window.showMaximized()