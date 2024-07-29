# -*- coding: utf-8 -*-
"""
Created on Mon Jul 29 18:35:38 2024

@author: Administrator
"""

import numpy as np

file = np.loadtxt('tempfile.txt', delimiter=',',unpack=True, dtype='str')
print('hola')
print(file)
np.savetxt('tempfile.txt', ['finger'], delimiter=',', fmt='%s')