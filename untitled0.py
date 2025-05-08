# -*- coding: utf-8 -*-
"""
Created on Mon Jul 29 18:35:38 2024

@author: Administrator
"""

import numpy as np
import matplotlib.pyplot as plt

td, ad, rd, ta, aa, ra = np.genfromtxt('iv708.csv', delimiter=',', skip_header = 1, unpack = True, dtype='str')
tdf = []
taf = []
for i in np.arange(0,len(td)):
    tdf.append(np.float64(str(td[i])))
for i in np.arange(0,len(ta)-2):
    taf.append(np.float64(str(ta[i])))
adf = []
sadf = []
rdf = []
srdf = []
for i in np.arange(0,len(ad)):
    adf.append(np.float64(str(ad[i]).split('±')[0]))
    rdf.append(np.float64(str(rd[i]).split('±')[0]))
    sadf.append(np.float64(str(ad[i]).split('±')[1]))
    srdf.append(np.float64(str(rd[i]).split('±')[1]))
aaf = []
saaf = []
raf = []
sraf = []
for i in np.arange(0,len(aa)-2):
    aaf.append(np.float64(str(aa[i]).split('±')[0]))
    raf.append(np.float64(str(ra[i]).split('±')[0]))
    saaf.append(np.float64(str(aa[i]).split('±')[1]))
    sraf.append(np.float64(str(ra[i]).split('±')[1]))
plt.errorbar(taf, aaf, yerr=saaf,capsize=1, fmt='o-')
plt.grid()
plt.xlabel('Temperatura')
plt.ylabel('A')
