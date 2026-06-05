# -*- coding: utf-8 -*-
"""
Created on Sun May 31 20:13:40 2026

@author: Charly
"""

import sys
sys.path.insert(0, r"C:\Users\Charly\NubeDF\PythonProgs\MisProgs") #para ASUS
#sys.path.insert(0, r"D:\NubeDF\PythonProgs\MisProgs") #para PC Facu

from figure_panel_assembler_v8 import launch_free_assembler
asm = launch_free_assembler()                       # vacío; agregás desde el panel
# o:  asm = launch_free_assembler(["fig1", "fig2.pdf", "fig3.png"])