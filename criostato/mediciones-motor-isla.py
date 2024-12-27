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
#import pymeasure.instruments.agilent as agi # type: ignore
from a34420a import *
import numpy as np # type: ignore
import time
from ls340 import *
from lsdrc91ca import *
from agie3643a import *
from hp34970a import *
import csv
from decimal import Decimal
w = 340

dpg.create_context()
dpg.create_viewport(title='Termo+Motor', width=800, height=500)

config_ls = np.genfromtxt('C:/tesis git/tesisfisica/criostato/configlsisla.txt', delimiter=',')
with dpg.value_registry():
    try:
        dpg.add_string_value(default_value=config_ls[4], tag="M_m")
    except IndexError:
        dpg.add_string_value(default_value=2.6, tag="M_m")

directory = "C:/tesis git/tesisfisica/criostato/Archivos"

#file_name = "nn" + str(time.strftime("%H:%M:%S", time.gmtime(time.time())))

with dpg.window(label="Archivo", width=w, height=130, pos=(0,0)):
    dpg.add_text("Elegir archivo.")
    dpg.add_button(label="Open File Explorer", callback=lambda: dpg.show_item("file_dialog"))
    dpg.add_text("", tag="selected_file_text")
    dpg.add_input_text(label="Muestra", tag="Muestra", default_value=f"{str(time.strftime("%Y-%m-%d"))+str(time.strftime("%H:%M:%S", time.gmtime(time.time())))}")

def add_row(values, ctrl=0):
    directory = dpg.get_value("selected_file_text")
    file_name = dpg.get_value("Muestra")
    if ctrl == 0:
        file_path = directory +'\\'+ file_name + '.csv'
    else:
        file_name = 'Control temperatura' + file_name + '.csv'
        file_path = directory + '/' + file_name + '.csv'
    try:
        with open(file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(values)
    except PermissionError:
        with open("C:/tesis git/tesisfisica/criostato/Archivos/test" + str(time.strftime("%H %M %S", time.localtime())), mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(values)

def file_selected_callback(sender, app_data):
    selected_file = app_data['file_path_name']
    dpg.set_value("selected_file_text", f"{selected_file}")
    print(f"File selected: {selected_file}")
    return

def open_file_dialog():
    dpg.show_item("file_dialog")
    return

t0_lectura = time.time()

t_plot = []
T_plot = []
Ts_plot = []
Pot_plot = []
r1_plot = []
r2_plot = []

def lecturas(mode = 'bip'): #esta funcion lee los aparatos y guarda todo lo que lee en el registro final
    data_t = time.strftime("%H %M %S", time.localtime())
    tiempo_pasar = time.time()-t0_lectura
    data_rs = []
    data_r = N_stat_msr()
    data_ls = data_r[2]
    dpg.set_value("tl", f'{data_ls[0]} K')
    dpg.set_value("sl", f'{data_ls[1]} K')
    dpg.set_value("pl", f'{data_ls[2]} %')
    supply = AgilentE3643A()
    dpg.set_value("vl", f'{np.round(float(supply.measure_voltage()),3)} V')
    dpg.set_value("r1l", f'{format((data_r[0]/data_r[1]),'.3e')} Ohm')
    r1_plot.append(data_r[0]/data_r[1])
    data_rs.append(data_r[0])
    data_rs.append(data_r[1])
    data_rs.append(data_r[0]/data_r[1])
    dpg.set_value("r2l", f'{format(data_r[0]/data_r[1],'.3e')} Ohm')
    r2_plot.append(data_r[0]/data_r[1])
    data_rs.append(data_r[0])
    data_rs.append(data_r[1])
    data_rs.append(data_r[0]/data_r[1])
    t_plot.append(float(tiempo_pasar))
    T_plot.append(data_ls[0])
    Ts_plot.append(data_ls[1])
    Pot_plot.append(data_ls[2])
    dpg.set_value("T_act_p", [t_plot, T_plot])
    dpg.set_value("T_setp_p", [t_plot, Ts_plot])
    dpg.set_value("Pot_p", [t_plot, Pot_plot])
    dpg.fit_axis_data('t_temp_ax')
    dpg.fit_axis_data('T_setp_y')
    dpg.set_value("r_1_p", [t_plot, r1_plot])
    dpg.set_value("r_2_p", [t_plot, r2_plot])
    dpg.fit_axis_data('t_temp_ax_m')
    dpg.fit_axis_data('Res_y')
    dpg.set_value("R1_p", [T_plot, r1_plot])
    dpg.fit_axis_data('t_temp_ax_r')
    dpg.fit_axis_data('rdt_y')
    dpg.set_value("R2_p", [T_plot, r2_plot])
    dpg.fit_axis_data('t_temp_ax_r')
    dpg.fit_axis_data('rdt_y')
    add_row([data_t, data_ls[0], data_ls[1], data_ls[2], data_rs[0], data_rs[1], data_rs[2], data_rs[3], data_rs[4], data_rs[5]])


dpg.add_file_dialog(directory_selector=True, show=False, callback=file_selected_callback, tag="file_dialog", width=700 ,height=400)

def N_stat_msr():
    mode = float(dpg.get_value('auto'))
    i_bias = dpg.get_value("i_bias")
    vlim = dpg.get_value("vlim")
    instrument_v = Agilent34420A("GPIB0::7::INSTR")
    instrument_v.set_range(dpg.get_value('v_range'))
    instrument_c = k224.KEITHLEY_224("GPIB0::2::INSTR")
    instrument_c.voltage = float(vlim)
    meas_v = []
    sent_i = []
    for i in np.arange(1, 1+int(dpg.get_value("N_stat"))):
        i_bias = dpg.get_value("i_bias")
        instrument_c.voltage = float(vlim)
        instrument_c.current = float(i_bias)
        instrument_c.operate = True
        med_v = instrument_v.measure_voltage()
        while float(instrument_v.custom_command('*OPC?')) != 1:
            print('opc?1')
        if mode == 1:
            if np.abs(float(med_v)) > float(dpg.get_value('v_scale_max')):
                if float(dpg.get_value("i_bias")) > 1e-9:
                    dpg.set_value("i_bias", format(float(i_bias)/10, '.3e'))
                pass
            elif np.abs(float(med_v)) < float(dpg.get_value('v_scale_min')):
                if float(dpg.get_value("i_bias")) < 10e-3:
                    dpg.set_value("i_bias", format(float(i_bias)*10, '.3e'))
                pass
        meas_v.append(np.abs(med_v))
        sent_i.append(np.abs(float(i_bias)))
    controller = LakeShoreDRC91CA()
    data_ls = [float(controller.read_temperature()), float(controller.get_setpoint()), float(controller.get_HTR())]
    for i in np.arange(1, 1+int(dpg.get_value("N_stat"))):
        i_bias = dpg.get_value("i_bias")
        instrument_c.voltage = float(vlim)
        instrument_c.current = -float(i_bias)
        instrument_c.operate = True
        med_v = instrument_v.measure_voltage()
        while float(instrument_v.custom_command('*OPC?')) != 1:
            print('opc?2')
        if mode == 1:
            if np.abs(float(med_v)) > float(dpg.get_value('v_scale_max')):
                if float(dpg.get_value("i_bias")) > 1e-9:
                    dpg.set_value("i_bias", format(float(i_bias)/10, '.3e'))
                pass
            elif np.abs(float(med_v)) < float(dpg.get_value('v_scale_min')):
                if float(dpg.get_value("i_bias")) < 10e-3:
                    dpg.set_value("i_bias", format(float(i_bias)*10, '.3e'))
                pass
        meas_v.append(np.abs(med_v))
        sent_i.append(np.abs(float(i_bias)))
    instrument_c.operate = False
    v_mean = np.mean(meas_v)
    i_mean = np.mean(sent_i)
    return [v_mean, i_mean, data_ls]

with dpg.window(label="Keithley 224", width=w, height=160, pos=(0,130)):
    dpg.add_text("V-Limit", pos=(20,20))
    V_Limit = dpg.add_input_text(label="V", default_value=f"{1}", tag="vlim", width=40, pos=(20,40))
    dpg.add_text("N biases", pos=(20, 60))
    N_stat = dpg.add_input_text(default_value=f"{3}", tag="N_stat", width=40, pos=(20,80))
    dpg.add_text("N mediciones", pos=(120, 60))
    Ctd_msr = dpg.add_input_text(default_value=f"{3}", tag="ctd_msr", width=40, pos=(120,80))
    dpg.add_text("Corriente bias", pos=(120, 20))
    i_bias = dpg.add_input_text(label="A", default_value=f"{0.001}", tag="i_bias", width=60, pos=(120,40))
    dpg.add_text("Autorange (1/0)", pos=(220, 20))
    auto_mode = dpg.add_input_text(default_value=f"{1}", tag="auto", width=60, pos=(220,40))
    dpg.add_text("Max. V", pos=(20, 100))
    v_scale_max = dpg.add_input_text(label="V", default_value=f"{0.01}", tag="v_scale_max", width=60, pos=(20,120))
    dpg.add_text("Mín. V", pos=(120, 100))
    v_scale_min = dpg.add_input_text(label="V", default_value=f"{0.001}", tag="v_scale_min", width=60, pos=(120,120))

with dpg.window(label="LSDRC91CA", width=w, height=60, pos=(0,290)):
    T_est = dpg.add_input_text(default_value=f"60", width=40,tag="T_est", pos=(20,40))
    dpg.add_text("Estabilidad (s)", pos=(20,20))
    motor = dpg.add_input_text(default_value=f"{dpg.get_value("M_m")}", width=40, tag="M_in", pos=(150, 40))
    dpg.add_text("Voltaje motor", pos=(150, 20))
    rvolt = dpg.add_input_text(default_value=f"{0.01}", width=40, tag="v_range", pos=(20, 80))
    dpg.add_text("Rango volt.", pos=(20, 60))
    dpg.add_button(label='Motor', callback=lambda:update_vars(), pos=(150,60))
    motorh = dpg.add_input_text(default_value=f"{4.8}", width=40, tag="mhi", pos=(270, 40))
    dpg.add_text("Motor Hi", pos=(270, 20))
    motorl = dpg.add_input_text(default_value=f"{1.2}", width=40, tag="mlo", pos=(150, 80))
    dpg.add_text("Motor Lo", pos=(270, 60))


def crea_tablas_T(sender, app_data, user_data):
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

def reset_table_T(sender, app_data, user_data):
    dpg.delete_item("Tabla", children_only= False)
    with dpg.table(header_row=True, tag="Tabla", borders_innerH=True, borders_outerH=True,
                        borders_innerV=True, borders_outerV=True, height = 450, no_host_extendY = True,
                        scrollY = True, parent="g_col"):
            dpg.add_table_column(label="T (K)")
            dpg.add_table_column(label="Rate (K/min)")
            dpg.add_table_column(label="Estable?")

def medicion_T(sender, app_data, user_data):
    try:
        dpg.remove_alias("tl")
        dpg.remove_alias("sl")
        dpg.remove_alias("rl")
        dpg.remove_alias("pl")
        dpg.remove_alias("r1l")
        dpg.remove_alias("r2l")
        dpg.remove_alias("pl")
        dpg.remove_alias("ttl")
        dpg.remove_alias("ttal")
        dpg.remove_alias("tal")
    except SystemError:
        pass
    with dpg.window(label="Control en vivo", width=w, height=240, pos=(0,390)):
        dpg.add_text("T actual (K)", pos=(10,20))
        t_actual_display = dpg.add_text("0.00 K", tag="tl", pos=(10,40))
        dpg.add_text("T setpoint (K)", pos=(180,20))
        setp_actual_display = dpg.add_text("0.00 K", tag="sl", pos=(180,40))
        dpg.add_text("Potencia (%)", pos=(10,60))
        pot_actual_display = dpg.add_text("0.00 %", tag="pl", pos=(10,80))
        dpg.add_text("Volt. motor (V)", pos=(180,60))
        pot_actual_display = dpg.add_text("2.6 V", tag="vl", pos=(180,80))
        dpg.add_text("R muestra 1", pos=(10,100))
        r1_actual_display = dpg.add_text("0.00e+0 Ohm", tag="r1l", pos=(10,120))
        dpg.add_text("R muestra 2", pos=(180,100))
        r2_actual_display = dpg.add_text("0.00e+0 Ohm", tag="r2l", pos=(180,120))
        dpg.add_text("Tiempo total", pos=(10,140))
        ttal_actual_display = dpg.add_text("00:00:00", tag="ttl", pos=(10,160))
        dpg.add_text("Tiempo tarea", pos=(180,140))
        tact_actual_display = dpg.add_text("00:00:00", tag="ttal", pos=(180,160))
        dpg.add_text("Tarea actual", pos=(10,180))
        tar_actual_display = dpg.add_text("AFK", tag="tal", pos=(10,200))
        add_row(['Tiempo', 'T(K)', 'Setpoint(K)', 'Heater','V muestra 1 (V)', 'I muestra 1 (A)', 'R muestra 1 (Ohm)', 'V muestra 2 (V)', 'I muestra 2 (A)', 'R muestra 2 (Ohm)'])
        medir_tabla_T()

def update_vars(): #esta funcion lee los parametros puestos en la ventana y los actualiza en vivo con el multithread
    instrument_c = k224.KEITHLEY_224("GPIB0::2::INSTR")
    instrument_c.voltage = float(dpg.get_value("vlim"))
    supply = AgilentE3643A()
    supply.apply(float(dpg.get_value("M_in")))
    np.savetxt('configlsisla.txt', [f'{0}, {0}, {0}, {0}, {dpg.get_value("M_in")}'], fmt='%s')

def ramp_T(T, rate):
    dpg.set_value('tal', "Rampa de temperatura")
    update_vars()
    t0 = time.time()
    t_report = 0
    controller = LakeShoreDRC91CA()
    current_setpoint = controller.read_temperature()
    target_setpoint = float(T)
    print(current_setpoint, target_setpoint, rate)
    if target_setpoint > current_setpoint and float(rate) < 0:
        rate = -float(rate)
    rampa = np.arange(float(current_setpoint), float(target_setpoint), float(rate)/12)
    try:
        rampa = np.append(rampa, target_setpoint)
    except IndexError:
        rampa = np.arange(float(current_setpoint), float(target_setpoint), float(-rate)/12)
        rampa = np.append(rampa, target_setpoint)
    v = 2.6
    for i in rampa:
        tK = time.time()
        while (time.time()-tK) < 60/12:
            update_vars()
            controller = LakeShoreDRC91CA()
            controller.set_setpoint(f'{np.round(i,2)}')
            supply = AgilentE3643A()
            supply.apply(v)
            T_real = controller.read_temperature()
            setpoint = i
            v = float(v)
            if float(T_real)>float(setpoint)+1.5 and v > 2.0 and float(controller.get_HTR())<10.0:
                v -= 0.1
            elif float(T_real)<float(setpoint)-1.5 and v < 3.0 and float(controller.get_HTR())>70.0:
                v += 0.1
            elif float(T_real)<float(setpoint)+1.5 and float(T_real)>float(setpoint)-1.5:
                v = 2.6
            lecturas()
            time.sleep(1)
            t_report = time.time()-t0
            dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t_report)))
            t_tot = time.time()-tiempo_total
            dpg.set_value('ttl', time.strftime("%H:%M:%S", time.gmtime(t_tot)))
    supply = AgilentE3643A()
    supply.apply(2.6)

tiempo_total = 0

#skip_ramp = 0

def medir_tabla_T():#a temperaturas fijas barre campos
    tiempo_total = time.time()
    update_vars()
    tiempo_start = time.time() #pongo tiempos iniciales y levanto las listas que se van a medir
    tiempo_est = 0
    controller = LakeShoreDRC91CA()
    algo_T = dpg.get_item_children("Tabla", 1)
    n = 0
    for fila in algo_T: #en cada temperatura corro el protocolo estabilizar
        parametros_T = dpg.get_item_children(fila, 1)
        update_vars() #estos updates sirven por si se actualizan parametros del PID, heater o medición
        setpoint = dpg.get_value(parametros_T[0])
        rate = dpg.get_value(parametros_T[1])
        ramp_T(setpoint, rate) #esto lleva la temperatura en rampa (ver ramp_T)
        controller = LakeShoreDRC91CA()
        T_real = controller.read_temperature()
        tiempo_est = time.time()
        v = 2.6
        while abs(float(T_real)-float(setpoint)) > 0.5: #mientras la diferencia es mayor a un porcentaje del setpoint no hace nada
            update_vars()
            algo_T = dpg.get_item_children("Tabla", 1)
            parametros_T = dpg.get_item_children(algo_T[n], 1)
            estable = dpg.get_value(parametros_T[2])
            estable = float(estable)
            controller = LakeShoreDRC91CA()
            T_real = controller.read_temperature()
            supply = AgilentE3643A()
            supply.apply(v)
            v = float(v)
            if float(T_real)>float(setpoint)+1 and v > 2.0 and float(controller.get_HTR())<10.0 :
                v -= 0.05
            elif float(T_real)<float(setpoint)-1 and v < 3.0 and float(controller.get_HTR())>70.0:
                v += 0.05
            elif float(T_real)<float(setpoint)+1 and float(T_real)>float(setpoint)-1:
                v = 2.6
            dpg.set_value("tal", "Esperando llegada al setpoint")
            lecturas() #esta funcion va a leer el Lakeshore, el nanovoltimetro y la fuente de alta corriente y va a guardar los datos
            tiempo_est = time.time()-tiempo_est
            t_tot = time.time()-tiempo_total
            dpg.set_value('ttl', time.strftime("%H:%M:%S", time.gmtime(t_tot))) #esto actualiza un tiempo para diagnostico, no representa lo guardado (tiempo real)
            dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(tiempo_est)))
            if (estable == 0 or estable == 0.00): #esto es por si se quiere saltear este punto
                break
            time.sleep(1)
        tiempo_est = time.time()
        v = 2.6
        while True: #una vez que se va abajo del threshold intenta estabilizar por x segundos
            supply = AgilentE3643A()
            supply.apply(v)
            algo_T = dpg.get_item_children("Tabla", 1)
            parametros_T = dpg.get_item_children(algo_T[n], 1)
            estable = dpg.get_value(parametros_T[2])
            estable = float(estable)
            T_real = controller.read_temperature() #acá abajo dice que si la diferencia es mayor a un porcentaje, empiece a contar otra vez
            v = float(v)
            if float(T_real)>float(setpoint)+1 and v < 2.0 and float(controller.get_HTR())<10.0:
                v += 0.1
            elif float(T_real)<float(setpoint)-1 and v > 3.0 and float(controller.get_HTR())>70.0:
                v -= 0.1
            elif float(T_real)<float(setpoint)+1 and float(T_real)>float(setpoint)-1:
                v = 2.6
            update_vars()
            dpg.set_value("tal", "Estabilizando temperatura")
            lecturas()
            tiempo_est = time.time()-tiempo_est
            t_tot = time.time()-tiempo_total
            dpg.set_value('ttl', time.strftime("%H:%M:%S", time.gmtime(t_tot))) #esto actualiza un tiempo para diagnostico, no representa lo guardado (tiempo real)
            dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(tiempo_est)))
            controller = LakeShoreDRC91CA()
            setpoint = float(setpoint)
            print(estable)
            print(type(estable))
            if abs(T_real-setpoint) > 1:#si es menor al porcentaje sigue contando, y si es menor y ya conto suficiente pare la
                tiempo_est = 0                      #estabilización
            if tiempo_est < float(dpg.get_value("T_est")):
                pass
            elif tiempo_est >= float(dpg.get_value("T_est")):
                break
            elif estable == 0 or estable == 0.00: #idem arriba por si se quiere saltar
                break
        for i in np.arange(1,int(dpg.get_value("ctd_msr"))): #hago muchas lecturas en cada campo, no se si es necesario
            if estable == 0 or estable == 0.0:
                break
            supply = AgilentE3643A()
            supply.apply(2.6)
            update_vars()
            lecturas(mode = 'bip')
        n += 1
        algo_T = dpg.get_item_children("Tabla", 1)
        n_max = len(algo_T)-1
    dpg.set_value("tal", "Terminado")
    #controller.write('CSET 1, A, 1, 0')

with dpg.window(label="Medición T", width=370, height=650, pos=(w,0)):
    T0m = dpg.add_input_text(default_value=f"{295}", width=40, tag="T0", pos=(20,40))
    dpg.add_text("T inicial (K)", pos=(20,20))
    Tm = dpg.add_input_text(default_value=f"{295}", width=40, tag="TF", pos=(150,40))
    dpg.add_text("T final (K)", pos=(150,20))
    sepm = dpg.add_input_text(default_value=f"{20}", width=40,tag="sep", pos=(270,40))
    dpg.add_text("dT (K)", pos=(270,20))
    ratem = dpg.add_input_text(default_value=f"{2}", width=40,tag="rate", pos=(20,80))
    dpg.add_text("Rate (K/min)", pos=(20,60))
    estm = dpg.add_input_text(default_value=f"{1}", width=40,tag="est", pos=(150,80))
    dpg.add_text("Estable? (1/0)", pos=(150,60))
    dpg.add_button(label="Agregar", callback=crea_tablas_T, pos=(270,80))
    with dpg.group(tag="g_col", pos=(10,120)):
        with dpg.table(header_row=True, tag="Tabla", borders_innerH=True, borders_outerH=True,
                        borders_innerV=True, borders_outerV=True, height = 450, no_host_extendY = True,
                        scrollY = True):
            dpg.add_table_column(label="T (K)")
            dpg.add_table_column(label="Rate (K/min)")
            dpg.add_table_column(label="Estable?")
    dpg.add_button(label="Limpiar", callback=reset_table_T, pos=(20,620))
    dpg.add_button(label="Comenzar", callback=medicion_T, pos=(240,620))

with dpg.window(label='Temperatura', pos=(w+370,0)):
    with dpg.plot(height=250, width=520):
            dpg.add_plot_axis(dpg.mvXAxis, label="Tiempo (s)", tag="t_temp_ax")
            dpg.add_plot_axis(dpg.mvYAxis, label="Temperatura (K)", tag="T_setp_y")
            dpg.add_scatter_series([], [], label="T Setpoint", parent="T_setp_y", tag="T_setp_p")
            dpg.add_scatter_series([], [], label="T Actual", parent="T_setp_y", tag="T_act_p")
            dpg.add_plot_axis(dpg.mvYAxis, label="Potencia (%)", tag="Pot_y")
            dpg.add_scatter_series([], [], label="Potencia", parent="Pot_y", tag="Pot_p")

with dpg.window(label='Muestra', pos=(w+370,285)):
    with dpg.plot(height=250, width=260):
            dpg.add_plot_axis(dpg.mvXAxis, label="Tiempo (s)", tag="t_temp_ax_m")
            dpg.add_plot_axis(dpg.mvYAxis, label="Resistencia (Ohm)", tag="Res_y")
            dpg.add_scatter_series([], [], label="Muestra 1", parent="t_temp_ax_m", tag="r_1_p")
            dpg.add_scatter_series([], [], label="Muestra 2", parent="t_temp_ax_m", tag="r_2_p")

with dpg.window(label='Resistencia', pos=(w+370+275,285)):
    with dpg.plot(height=250, width=260):
            dpg.add_plot_axis(dpg.mvXAxis, label="Temperatura (K)", tag="t_temp_ax_r")
            dpg.add_plot_axis(dpg.mvYAxis, label="Resistencia (Ohm)", tag="rdt_y")
            dpg.add_scatter_series([], [], label="Resistencia 1", parent="t_temp_ax_r", tag="R1_p")
            dpg.add_scatter_series([], [], label="Resistencia 2", parent="t_temp_ax_r", tag="R2_p")

dpg.setup_dearpygui()
dpg.maximize_viewport()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()