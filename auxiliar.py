#%%
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  8 15:05:04 2024

@author: Administrator
"""

import numpy as np
import matplotlib.pyplot as plt

T = [295,270,250,230,210,190,170,150,130,110,90,80]
Tb = [280,260,240,220,200,180,160,140,120,100]
t = np.concatenate((T,Tb))


A = [2.808e-03,3.302e-03,1.169e-04,2.573e-03,6.320e-04,1.404e-03,1.6e-03,1.005e-03,8.655e-04,4.753e-04,3.236e-04,2.464e-04]
Ab = [1.97e-03,2.652e-03,1.46e-03,1.618e-03,1.274e-03,1.033e-03,6.645e-04,7.121e-04,4.125e-04,2.812e-04]
a = np.concatenate((A,Ab))

R = [22.205,38.635,37.572,50.848,60.911,83.712,142.270,226.394,251.732,507.971,789.166,907.546] #kohm
Rb = [26.169,32.421,38.020,52.951,98.432,250.974,312.865,494.964,642.656,916.187]
r = np.concatenate((R,Rb))
#%%
fig = plt.figure(figsize=(10,5))
#mng = plt.get_current_fig_manager()
#mng.window.showMaximized()

# First subplot (top-left)
ax1 = plt.subplot(1,2,1)
sc1 = ax1.scatter(1/np.array(t), a, c=t, cmap='cool')
ax1.set_xlabel('1/T (1/K)')
ax1.set_ylabel('A')
ax1.set_title('A vs T en')

# Second subplot (bottom-left)
ax2 = plt.subplot(1,2,2)
sc2 = ax2.scatter(np.ones_like(t)/t, np.log(r), c=t, cmap='cool')
ax2.set_xlabel('1/T (1/K)')
ax2.set_ylabel('Log(R)')
ax2.set_title('R vs T')

ax1.grid()
ax2.grid()

plt.show()
#%%
fig = plt.figure(figsize=(10,5))
# First subplot (top-left)
ax1 = plt.subplot(1,2,1)
sc1 = ax1.scatter(T, A, c=T, cmap='cool', marker='o', label='Subida')
ax1.set_xlabel('T (K)')
ax1.set_ylabel('A')
ax1.set_title('A vs T en subida')

# Second subplot (bottom-left)
ax2 = plt.subplot(1,2,2)
sc2 = ax2.scatter(np.ones_like(T)/T, np.log(R), c=T, cmap='cool', marker='o', label='Subida')
ax2.set_xlabel('1/T (1/K)')
ax2.set_ylabel('Log(R) (k$\Omega$?)')
ax2.set_title('R vs T en subida')

# First subplot (top-left)
ax1 = plt.subplot(1,2,1)
sc1 = ax1.scatter(Tb, Ab, c=Tb, cmap='cool', marker='x', label='Bajada')
ax1.set_xlabel('T (K)')
ax1.set_ylabel('A')
ax1.set_title('A vs T en bajada')

# Second subplot (bottom-left)
ax2 = plt.subplot(1,2,2)
sc2 = ax2.scatter(np.ones_like(Tb)/Tb, np.log(Rb), c=Tb, cmap='cool', marker='x', label='Bajada')
ax2.set_xlabel('1/T (1/K)')
ax2.set_ylabel('R (k$\Omega$)')
#ax2.set_yscale('log')
ax2.set_title('R vs T en bajada')

ax1.grid(True)
ax2.grid(True)
plt.legend()
plt.suptitle('Ajustes SCLC n=2 Cristales viejos')
plt.tight_layout()
plt.show()
# %%
