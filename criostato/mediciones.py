# -*- coding: utf-8 -*-
"""
Created on Wed Aug 28 14:42:05 2024

@author: Administrator
"""
import os
import os.path
import sys
os.chdir("C:/tesis git/tesisfisica/criostato")
import dearpygui.dearpygui as dpg
import k224
import pymeasure.instruments.agilent as agi
import numpy as np
import time
w = 380


dpg.create_context()
dpg.create_viewport(title='Custom Title', width=800, height=500)

def file_selected_callback(sender, app_data):
    selected_file = app_data['file_path_name']
    dpg.set_value("selected_file_text", f"Selected File: {selected_file}")
    print(f"File selected: {selected_file}")
    return

def open_file_dialog():
    dpg.show_item("file_dialog")
    return

dpg.add_file_dialog(directory_selector=True, show=False, callback=file_selected_callback, tag="file_dialog", width=700 ,height=400)

with dpg.window(label="Archivo", width=w, height=130, pos=(0,0)):
    dpg.add_text("Click the button to open the file explorer.")
    dpg.add_button(label="Open File Explorer", callback=lambda: dpg.show_item("file_dialog"))
    dpg.add_text("", tag="selected_file_text")
    dpg.add_input_text(label="Muestra", default_value="")
    
def k224open(sender, app_data, user_data):
    ilim = dpg.get_value("ilim")
    vlim = dpg.get_value("vlim")
    per = dpg.get_value("per")
    instrument = k224.KEITHLEY_224("GPIB0::2::INSTR", ilim, vlim)
    input_value = dpg.get_value(user_data)
    i_max = float(input_value)
    valores_rampa = np.linspace(0,i_max,5)
    valoresx = []
    valoresy = []
    for i in ["pos", "neg"]:
        for i in np.arange(0,len(valores_rampa)):
            print(valores_rampa[i])
            instrument.current = valores_rampa[i]
            meas_c = instrument.get_measurement().current
            valoresx.append(i)
            valoresy.append(meas_c)
            dpg.set_value("c_plot", [valoresx, valoresy])
            dpg.fit_axis_data('x_axis')
            dpg.fit_axis_data('y_axis')
            time.sleep(0.1)
        for i in np.arange(0,len(valores_rampa)):
            print(valores_rampa[-i-1])
            instrument.current = valores_rampa[-i-1]
            meas_c = instrument.get_measurement().current
            valoresx.append(i+len(valores_rampa))
            valoresy.append(meas_c)
            dpg.set_value("c_plot", [valoresx, valoresy])
            dpg.fit_axis_data('x_axis')
            dpg.fit_axis_data('y_axis')
            time.sleep(0.1)

def a34420m(sender, app_data, user_data):
    instrument_v = agi.Agilent34410A("GPIB0::7::INSTR")
    valoresvn = []
    valoresv = []
    for i in np.arange(0,5):
            vmed = instrument_v.voltage_dc
            valoresvn.append(i)
            valoresv.append(vmed)
            dpg.set_value("v_plot", [valoresvn, valoresv])
            dpg.fit_axis_data('VN_axis')
            dpg.fit_axis_data('V_axis')
            time.sleep(0.1)
            
with dpg.window(label="Keithley 224", width=w, height=200, pos=(0,130)):
    dpg.add_text("Rampa")
    I_max = dpg.add_input_text(label="0-x", default_value="0.005")
    dpg.add_button(label="k224", callback=k224open, user_data=I_max)
    dpg.add_text("I-Limit")
    I_Limit = dpg.add_input_text(label="I (A)", default_value=f"{0.000001}", tag="ilim")
    dpg.add_text("V-Limit")
    V_Limit = dpg.add_input_text(label="V (V)", default_value=f"{1}", tag="vlim")

with dpg.window(label="LS 340", width=w, pos=(0,330)):
    dpg.add_button(label="Temp?", callback=lambda:print('0K'))

def crea_tablas(sender, app_data, user_data):
    T0 = float(dpg.get_value("T0"))
    TF = float(dpg.get_value("TF"))
    sep = float(dpg.get_value("sep"))
    rate = float(dpg.get_value("rate"))
    if (T0>TF):
        rate = -(rate)
    est = dpg.get_value("est")
    N = int(np.abs(T0-TF)/sep) + 1
    tes = np.round(np.linspace(T0, TF, N),1)
    data_row = [tes, np.full_like(tes, rate), np.full_like(tes, est)]
    for i in range(0, N):
            with dpg.table_row(parent="Tabla"):
                for j in range(0, 3):
                    dpg.add_input_text(default_value=f"{data_row[j][i]}")

def reset_table(sender, app_data, user_data):
    dpg.delete_item("Tabla", children_only= False)
    with dpg.table(header_row=True, tag="Tabla", borders_innerH=True, borders_outerH=True,
                        borders_innerV=True, borders_outerV=True, height = 430, no_host_extendY = True,
                        scrollY = True, parent="g_col"):
            dpg.add_table_column(label="T (K)")
            dpg.add_table_column(label="Rate (K/min)")
            dpg.add_table_column(label="Estable?")

with dpg.window(label="Medición", width=w, height=650, pos=(340,0)):
    T0m = dpg.add_input_text(default_value=f"{295}", width=40, tag="T0", pos=(20,40))
    dpg.add_text("T inicial (K)", pos=(20,20))
    Tm = dpg.add_input_text(default_value=f"{100}", width=40, tag="TF", pos=(150,40))
    dpg.add_text("T final (K)", pos=(150,20))
    sepm = dpg.add_input_text(default_value=f"{20}", width=40,tag="sep", pos=(270,40))
    dpg.add_text("Ctd. puntos", pos=(270,20))
    ratem = dpg.add_input_text(default_value=f"{2}", width=40,tag="rate", pos=(20,80))
    dpg.add_text("Rate (K/min)", pos=(20,60))
    estm = dpg.add_input_text(default_value=f"{1}", width=40,tag="est", pos=(150,80))
    dpg.add_text("Estable? (1/0)", pos=(150,60))
    dpg.add_button(label="Agregar", callback=crea_tablas, pos=(270,80))
    with dpg.group(tag="g_col", pos=(10,120)):
        with dpg.table(header_row=True, tag="Tabla", borders_innerH=True, borders_outerH=True,
                        borders_innerV=True, borders_outerV=True, height = 430, no_host_extendY = True,
                        scrollY = True):
            dpg.add_table_column(label="T (K)")
            dpg.add_table_column(label="Rate (K/min)")
            dpg.add_table_column(label="Estable?")
    dpg.add_button(label="Limpiar", callback=reset_table, pos=(150,560))
    dpg.add_text("T actual (K)", pos=(34,580))
    dpg.add_text("T setpoint (K)", pos=(w/2+34,580))
    dpg.add_text("Rate (K/min)", pos=(34,620))
    dpg.add_text("Potencia (K)", pos=(w/2+34,620))

with dpg.window(label='IvN', pos=(600,400)):
    with dpg.plot(label="XY Plot", height=250, width=250):
            dpg.add_plot_axis(dpg.mvXAxis, label="X Axis", tag="x_axis")
            dpg.add_plot_axis(dpg.mvYAxis, label="Y Axis", tag="y_axis")
            dpg.add_line_series([], [], label="Series 1", parent="y_axis", tag="c_plot")

with dpg.window(label='VvN', pos=(850,0)):
    with dpg.plot(label="VXY Plot", height=250, width=250):
            dpg.add_plot_axis(dpg.mvXAxis, label="N", tag="VN_axis")
            dpg.add_plot_axis(dpg.mvYAxis, label="V", tag="V_axis")
            dpg.add_line_series([], [], label="Series V", parent="V_axis", tag="v_plot")



dpg.setup_dearpygui()
dpg.maximize_viewport()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()