# -*- coding: utf-8 -*-
"""
Created on Mon Jul 29 18:35:38 2024

@author: Administrator
"""

import numpy as np
import matplotlib.pyplot as plt

td, ad, rd, ta, aa, ra = np.genfromtxt('iv708.csv', delimiter=',', skip_header = 1, unpack = True, dtype='str')
print(len(aa))
for i in np.arange(0,len(ad)):
    ad[i] = float(str(ad[i]).split('Â±')[0])
    rd[i] = float(str(rd[i]).split('Â±')[0])
print(aa)
for i in np.arange(0,len(aa)-2):
    type(aa[i])
    aa[i] = np.float64(str(aa[i]).split('Â±')[0])
    type(aa[i])
    ra[i] = float(str(ra[i]).split('Â±')[0])
print(aa)
plt.scatter(td, ad)
plt.grid()
