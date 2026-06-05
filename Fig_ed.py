# -*- coding: utf-8 -*-
"""
Created on Sun Feb 23 20:42:00 2025

@author: Charly

Este script nos deja ver y editar campos de figuras que armamos previamente
y que procesamos y guardamos con funciones del script figure_editor.py
Este script guardó la data en archivos .csv y la parte "cosmética" de la figura
en un archivo .json
Abajo se ven los ejemplos de cómo cargar y editar estas figs


"""
#%%
### Ponemos en el path e importamos las funciones de 'figure_editor'   
import sys

# -------------------------------------------------------------------------
# Backend interactivo recomendado para Spyder.
# IMPORTANTE: si Spyder ya cargó matplotlib en modo inline, a veces el cambio
# programático no alcanza. En ese caso ejecutar en la consola:
#     %matplotlib qt
# y luego volver a correr este script.
# -------------------------------------------------------------------------


import matplotlib.pyplot as plt
plt.ion()


# sys.path.insert(0, r"C:\Users\Charly\NubeDF\PythonProgs\MisProgs") #para ASUS
#sys.path.insert(0, r"D:\NubeDF\PythonProgs\MisProgs") #para PC Facu
from figure_editor5 import save_figure_data, load_figure, edit_cosmetics


#%% Borramos todas las figs?

# plt.close('all')


#%% Cargamos y recreamos una fig guardada con este script: escribir entre "" el nombre sin las extensiones .json ni .csv

fig_ed = load_figure("fig 11")


#%% Luego, editamos su cosmética

fig = edit_cosmetics(fig_ed)

# (Nota: la función se llama edit_cosmetics y espera el objeto figura, no una cadena)
# La función desplegará un menú interactivo en la consola para modificar diversos aspectos cosméticos.


#%% Guardamos la fig editada con toda su info cosmética y data

# save_figure_data(fig, filename="figure") #el nombre que elegimos para su archivo


#%% O guardamos una fig en particular que vemos graficada con toda su info cosmética (.json) y data (.csv)

# figxx = plt.figure(1)  # El número de figura que aparece en el panel
# save_figure_data(figxx, filename="A_Nyquist") #el nombre que elegimos para su archivo
