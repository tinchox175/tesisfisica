# -*- coding: utf-8 -*-
"""
Created on Wed Aug 28 14:42:05 2024

@author: Administrator
"""
import os
import os.path
import sys
import dearpygui.dearpygui as dpg # type: ignore
import k224
import pymeasure.instruments.agilent as agi # type: ignore
import numpy as np # type: ignore
import time
from ls340 import *
w = 340


dpg.create_context()
dpg.create_viewport(title='Custom Title', width=800, height=500)

config_ls = np.genfromtxt('configls.txt', delimiter=',')
with dpg.value_registry():
    #try:
        dpg.add_string_value(default_value=config_ls[0], tag="P_m")
        dpg.add_string_value(default_value=config_ls[1], tag="I_m")
        dpg.add_string_value(default_value=config_ls[2], tag="D_m")
        dpg.add_string_value(default_value=config_ls[3], tag="HR")
    #except IndexError:
    #    dpg.add_string_value(default_value="200", tag="P_m")
    #    dpg.add_string_value(default_value="30", tag="I_m")
    #    dpg.add_string_value(default_value="0", tag="D_m")
    #    dpg.add_string_value(default_value="0", tag="HR")

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

def N_stat_msr(sender, app_data, user_data):
    i_bias = dpg.get_value("i_bias")
    ilim = dpg.get_value("ilim")
    vlim = dpg.get_value("vlim")
    instrument_v = agi.Agilent34410A("GPIB0::7::INSTR")
    instrument_c = k224.KEITHLEY_224("GPIB0::2::INSTR", ilim, vlim)
    sent_c = []
    enes = []
    meas_v = []
    for i in np.arange(1, 1+int(dpg.get_value("N_stat"))):
        send_c = instrument_c.current = float(i_bias)
        time.sleep(0.0003)
        med_v = instrument_v.voltage_dc
        time.sleep(0.0003)
        instrument_c.current = 0
        enes.append(i)
        meas_v.append(med_v)
        sent_c.append(send_c)
        dpg.set_value("v_plot", [enes, meas_v])
        dpg.fit_axis_data('NV_axis')
        dpg.fit_axis_data('V_axis')
        dpg.set_value("c_plot", [enes, sent_c])
        dpg.fit_axis_data('NI_axis')
        dpg.fit_axis_data('I_axis')
    for i in np.arange(1, 1+int(dpg.get_value("N_stat"))):
        send_c = instrument_c.current = -float(i_bias)
        time.sleep(0.0003)
        med_v = instrument_v.voltage_dc
        time.sleep(0.0003)
        instrument_c.current = 0
        enes.append(i+int(dpg.get_value("N_stat")))
        meas_v.append(med_v)
        sent_c.append(send_c)
        dpg.set_value("v_plot", [enes, meas_v])
        dpg.fit_axis_data('NV_axis')
        dpg.fit_axis_data('V_axis')
        dpg.set_value("c_plot", [enes, sent_c])
        dpg.fit_axis_data('NI_axis')
        dpg.fit_axis_data('I_axis')

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
            dpg.fit_axis_data('NI_axis')
            dpg.fit_axis_data('I_axis')
            time.sleep(0.1)
        for i in np.arange(0,len(valores_rampa)):
            print(valores_rampa[-i-1])
            instrument.current = valores_rampa[-i-1]
            meas_c = instrument.get_measurement().current
            valoresx.append(i+len(valores_rampa))
            valoresy.append(meas_c)
            dpg.set_value("c_plot", [valoresx, valoresy])
            dpg.fit_axis_data('NI_axis')
            dpg.fit_axis_data('I_axis')
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
    dpg.add_text("N mediciones")
    N_stat = dpg.add_input_text(default_value=f"{4}", tag="N_stat")
    dpg.add_text("Corriente bias")
    i_bias = dpg.add_input_text(default_value=f"{0.0005}", tag="i_bias")
    dpg.add_button(label="Med. Stat.", callback=N_stat_msr)

def update_HR(sender, app_data, user_data):
    hr_new = f'{user_data}'
    dpg.set_value("HR", hr_new)
    controller = LakeShore340(gpib_address=12)
    controller.write(f'RANGE 1, {hr_new}')
    controller.close()
    dpg.set_value(heater_display_text, f"{hr_new}")
    np.savetxt('configls.txt', [f'{dpg.get_value("P_in")}, {dpg.get_value("I_in")}, {dpg.get_value("D_in")}, {dpg.get_value("HR")}'], fmt='%s')

def update_PID(sender, app_data, user_data):
    controller = LakeShore340(gpib_address=12)
    controller.write(f'PID 1, {dpg.get_value("P_in")}, {dpg.get_value("I_in")}, {dpg.get_value("D_in")}')
    controller.close()
    np.savetxt('configls.txt', [f'{dpg.get_value("P_in")}, {dpg.get_value("I_in")}, {dpg.get_value("D_in")}, {dpg.get_value("HR")}'], fmt='%s')

with dpg.window(label="LS 340", width=w, height=200, pos=(0,330)):
    P = dpg.add_input_text(default_value=f"{dpg.get_value("P_m")}", width=40, tag="P_in", pos=(20,40), callback=update_PID)
    dpg.add_text("P", pos=(20,20))
    I = dpg.add_input_text(default_value=f"{dpg.get_value("I_m")}", width=40, tag="I_in", pos=(140,40), callback=update_PID)
    dpg.add_text("I", pos=(150,20))
    D = dpg.add_input_text(default_value=f"{dpg.get_value("D_m")}", width=40,tag="D_in", pos=(270,40), callback=update_PID)
    dpg.add_text("D", pos=(270,20))
    T_est = dpg.add_input_text(default_value=f"60", width=40,tag="T_est", pos=(20,82))
    dpg.add_text("Tiempo estable (s)", pos=(20,62))
    with dpg.group(tag="g_hr", pos=(140,82)):
        with dpg.menu(label="Heater Range:"):
            dpg.add_menu_item(label="OFF", callback=update_HR, user_data = "0")
            dpg.add_menu_item(label="1", callback=update_HR, user_data = "1")
            dpg.add_menu_item(label="2", callback=update_HR, user_data = "2")
            dpg.add_menu_item(label="3", callback=update_HR, user_data = "3")
            dpg.add_menu_item(label="4", callback=update_HR, user_data = "4")
            dpg.add_menu_item(label="MAX", callback=update_HR, user_data = "5")
    heater_display_text = dpg.add_text(dpg.get_value("HR"), pos=(240, 79))


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

def temperatura(row):
    """""
    Pseudocódigo:
    T, rate, estable = row
    controller.setpoint = T[i]
    controller.rate = rate[i]
    tiempo_total = 0
    if estable[i] == 1:
        tiempo_est = 0
        while abs(T_real-setpoint) > setpoint*0.01:
            time.sleep(1)
            data_ls = controller.msr()
            dpg.set_value("T_actual", data_ls[0])
            dpg.set_value("T_setpoint", data_ls[1])
            dpg.set_value("rate", data_ls[2])
            dpg.set_value("Pwr", data_ls[3])
            add_row(data_ls, f'control_temperatura_{muestra}')
            tiempo_est +=1
            tiempo_total +=1
            dpg.set_value("Tiempo ciclo", tiempo_est)
        tiempo_est = 0
        while abs(T_real-setpoint) < setpoint*0.01:
            time.sleep(1)
            data_ls = controller.msr()
            dpg.set_value("T_actual", data_ls[0])
            dpg.set_value("T_setpoint", data_ls[1])
            dpg.set_value("rate", data_ls[2])
            dpg.set_value("Pwr", data_ls[3])
            add_row(data_ls, f'control_temperatura_{muestra}')
            tiempo_est +=1
            tiempo_total +=1
            if tiempo_est < int(dpg.get_value("T_est)):
                pass
            elif tiempo_est > int(dpg.get_value("T_est):
                break
        temperatura(row)
    elif estable[i] == 0:
        tiempo_est = 0
        while abs(T_real-setpoint) > setpoint*0.01:
            time.sleep(1)
            data_ls = controller.msr()
            dpg.set_value("T_actual", data_ls[0])
            dpg.set_value("T_setpoint", data_ls[1])
            dpg.set_value("rate", data_ls[2])
            dpg.set_value("Pwr", data_ls[3])
            add_row(data_ls, f'control_temperatura_{muestra}')
            tiempo_est +=1
            tiempo_total +=1
            dpg.set_value("Tiempo ciclo", tiempo_est)
    return
    """""
    return

def medir(sender, app_data, user_data):
    """""
    Pseudocódigo:
    data = 4_terminales()
    plots(data)
    add_row(data, f'medicion_{lista_setpoints[i]}_{muestra}') ???
    """""
    return
def medicion_T_full(sender, app_data, user_data):
    """""
    Pseudocódigo:
    create_window('info')
    create_file(f"control_temperatura_{muestra}")
    for i in rows:
        create_file(f"medicion_{lista_setpoints[i]}_{muestra}") ???
        temperatura(i)
        medir()
    """""
    return

with dpg.window(label="Medición", width=w+30, height=700, pos=(w,0)):
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
    dpg.add_button(label="Limpiar", callback=reset_table, pos=(20,560))
    dpg.add_text("T actual (K)", tag="T_actual_live", pos=(34,580))
    t_actual_display = dpg.add_text("0.00 K", pos=(34,600))
    dpg.add_text("T setpoint (K)", tag="T_setpoint_live", pos=(w/2+34,580))
    setp_actual_display = dpg.add_text("0.00 K", pos=(w/2+34,600))
    dpg.add_text("Rate (K/min)", tag="rate_live", pos=(34,620))
    rate_actual_display = dpg.add_text("0.00", pos=(34,640))
    dpg.add_text("Potencia", tag="Pwr_live", pos=(w/2+34,620))
    pot_actual_display = dpg.add_text("0.00 %", pos=(w/2+34,640))
    dpg.add_button(label="Comenzar", callback=print('lesgoo'), pos=(140,670))

with dpg.window(label='I bias', pos=(600,400)):
    with dpg.plot(label="I vs N Plot", height=250, width=250):
            dpg.add_plot_axis(dpg.mvXAxis, label="N", tag="NI_axis")
            dpg.add_plot_axis(dpg.mvYAxis, label="I", tag="I_axis")
            dpg.add_line_series([], [], label="Series 1", parent="I_axis", tag="c_plot")

with dpg.window(label='V bias', pos=(850,0)):
    with dpg.plot(label="V vs N", height=250, width=250):
            dpg.add_plot_axis(dpg.mvXAxis, label="N", tag="NV_axis")
            dpg.add_plot_axis(dpg.mvYAxis, label="V", tag="V_axis")
            dpg.add_line_series([], [], label="Series V", parent="V_axis", tag="v_plot")


dpg.setup_dearpygui()
dpg.maximize_viewport()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()