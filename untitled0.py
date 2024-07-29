# -*- coding: utf-8 -*-
"""
Created on Tue Jul 23 21:18:14 2024

@author: Jerik
"""
import matplotlib.pyplot as plt
import numpy as np

# Example data generation (replace this with your actual data)
np.random.seed(0)
time = np.linspace(0, 10, 100)
voltage = np.linspace(-1, 1, 100)
I = np.random.normal(0, 0.002, 100)
R_inst = np.random.normal(0, 1000, 100)
R_rem = np.random.normal(0, 5000, 100)
gamma = np.random.normal(0, 10, 100)

fig = plt.figure()

# First subplot (top-left)
ax1 = plt.subplot2grid((2, 3), (0, 0))
sc1 = ax1.scatter(voltage, I, c=time, cmap='cool')
ax1.set_xlabel('V (V)')
ax1.set_ylabel('I (mA)')
ax1.set_title('I vs V')

# Second subplot (bottom-left)
ax2 = plt.subplot2grid((2, 3), (1, 0))
sc2 = ax2.scatter(voltage, I, c=time, cmap='cool')
ax2.set_xlabel('Voltage (V)')
ax2.set_ylabel('γ')
ax2.set_title('γ vs V')

# Third subplot (top-right)
ax3 = plt.subplot2grid((2, 3), (0, 1), rowspan=2)
sc3 = ax3.scatter(voltage, R_inst, c=time, cmap='cool')
ax3.set_xlabel('Voltage (V)')
ax3.set_ylabel('R_inst (kΩ)')
ax3.set_title('R_inst vs V')

# Fourth subplot (bottom-right)
ax4 = plt.subplot2grid((2, 3), (0, 2), rowspan=2)
sc4 = ax4.scatter(voltage, R_rem, c=time, cmap='cool')
ax4.set_xlabel('Voltage (V)')
ax4.set_ylabel('R_rem (kΩ)')
ax4.set_title('R_rem vs V')
cbar4 = plt.colorbar(sc4, ax=ax4)
cbar4.set_label('Time [s]')

plt.show()