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
from ls625 import *
from hp34970a import *
import csv
w = 340


dpg.create_context()
dpg.create_viewport(title='Criostato 9T', width=800, height=500)

config_ls = np.genfromtxt('configls.txt', delimiter=',')
with dpg.value_registry():
    try:
        dpg.add_string_value(default_value=config_ls[0], tag="P_m")
        dpg.add_string_value(default_value=config_ls[1], tag="I_m")
        dpg.add_string_value(default_value=config_ls[2], tag="D_m")
        dpg.add_string_value(default_value=config_ls[3], tag="HR_m")
        dpg.add_string_value(default_value="0", tag="I_actual")
    except IndexError:
        dpg.add_string_value(default_value="200", tag="P_m")
        dpg.add_string_value(default_value="30", tag="I_m")
        dpg.add_string_value(default_value="0", tag="D_m")
        dpg.add_string_value(default_value="0", tag="HR_m")

directory = "C:/tesis git/tesisfisica/criostato"

file_name = "test" + str(np.random.random())

def add_row(values, ctrl=0):
    directory = dpg.get_value("selected_file_text")
    file_name = dpg.get_value("Muestra")
    if ctrl == 0:
        file_path = os.path.join(directory, file_name, '.csv')
    else:
        file_name = 'Control temperatura' + file_name + '.csv'
        file_path = os.path.join(directory, file_name)
    with open(file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(values)

def file_selected_callback(sender, app_data):
    selected_file = app_data['file_path_name']
    dpg.set_value("selected_file_text", f"Selected File: {selected_file}")
    print(f"File selected: {selected_file}")
    return

def open_file_dialog():
    dpg.show_item("file_dialog")
    return

t0_lectura = time.time()

def lecturas(): #esta funcion lee los aparatos y guarda todo lo que lee en el registro final
    data_t = time.strftime("%H %M %S", time.localtime())
    tiempo_pasar = time.time()-t0_lectura
    controller = LakeShore340(gpib_address=12)
    fuente = LakeShore625(11)
    switch = hp34970()
    data_ls = [float(controller.read_temperature(1)), float(controller.get_setpoint(1)), float(controller.query('HTR?'))]
    dpg.set_value("tl", data_ls[0])
    dpg.set_value("sl", data_ls[1])
    dpg.set_value("pl", data_ls[2])
    switch.open_channels([211,212,221,222])
    switch.close_channels([211,221])
    data_rs = []
    data_r = N_stat_msr()
    dpg.set_value("r1l", data_r[0]/data_r[1])
    r1_plot.append(data_r[0]/data_r[1])
    data_rs.append(data_r[0])
    data_rs.append(data_r[1])
    data_rs.append(data_r[0]/data_r[1])
    switch = hp34970()
    controller = LakeShore340(gpib_address=12)
    fuente = LakeShore625(11)
    switch.open_channels([211,212,221,222])
    switch.close_channels([212,222])
    data_r = N_stat_msr()
    switch = hp34970()
    controller = LakeShore340(gpib_address=12)
    fuente = LakeShore625(11)
    dpg.set_value("r2l", data_r[0]/data_r[1])
    r2_plot.append(data_r[0]/data_r[1])
    data_rs.append(data_r[0])
    data_rs.append(data_r[1])
    data_rs.append(data_r[0]/data_r[1])
    data_b = [float(fuente.get_current()), float(fuente.get_voltage()), 1.1914*float(fuente.get_current())]
    dpg.set_value("if", data_b[0])
    dpg.set_value("vb", data_b[1])
    dpg.set_value("hel", data_b[2])
    t_plot.append(float(tiempo_pasar))
    T_plot.append(data_ls[0])
    Ts_plot.append(data_ls[1])
    Pot_plot.append(data_ls[2])
    Ib_plot.append(data_b[0])
    dpg.set_value("T_act_p", [t_plot, T_plot])
    dpg.set_value("T_setp_p", [t_plot, Ts_plot])
    dpg.set_value("Pot_p", [t_plot, Pot_plot])
    dpg.fit_axis_data('t_temp_ax')
    dpg.fit_axis_data('T_setp_y')
    dpg.set_value("r_1_p", [t_plot, r1_plot])
    dpg.set_value("r_2_p", [t_plot, r2_plot])
    dpg.fit_axis_data('t_temp_ax_m')
    dpg.fit_axis_data('Res_y')
    dpg.set_value("H_p", [t_plot, Ib_plot])
    dpg.fit_axis_data('t_temp_ax_c')
    dpg.fit_axis_data('Curr_y')
    add_row([data_t, data_ls[0], data_ls[1], data_ls[2], data_rs[0], data_rs[1], data_rs[2], data_rs[3], data_rs[4], data_rs[5], data_b[0], data_b[1], data_b[2]])


dpg.add_file_dialog(directory_selector=True, show=False, callback=file_selected_callback, tag="file_dialog", width=700 ,height=400)

with dpg.window(label="Archivo", width=w, height=130, pos=(0,0)):
    dpg.add_text("Elegir archivo.")
    dpg.add_button(label="Open File Explorer", callback=lambda: dpg.show_item("file_dialog"))
    dpg.add_text("", tag="selected_file_text")
    dpg.add_input_text(label="Muestra", tag="Muestra", default_value="Test")

def N_stat_msr():
    i_bias = dpg.get_value("i_bias")
    vlim = dpg.get_value("vlim")
    instrument_v = agi.Agilent34410A("GPIB0::7::INSTR")
    instrument_c = k224.KEITHLEY_224("GPIB0::2::INSTR")
    instrument_c.voltage = float(vlim)
    meas_v = []
    sent_i = []
    for i in np.arange(1, 1+int(dpg.get_value("N_stat"))):
        instrument_c.voltage = float(vlim)
        instrument_c.current = float(i_bias)
        instrument_c.operate = True
        time.sleep(0.1)
        med_v = instrument_v.voltage_dc
        if float(med_v) > 0.01:
            dpg.set_value("i_bias", float(i_bias)/10)
            instrument_c.operate = False
            time.sleep(0.1)
            pass
        elif float(med_v) < 0.001:
            dpg.set_value("i_bias", float(i_bias)*10)
            instrument_c.operate = False
            time.sleep(0.1)
            pass
        time.sleep(0.1)
        instrument_c.operate = False
        meas_v.append(med_v)
        sent_i.append(float(i_bias))
    for i in np.arange(1, 1+int(dpg.get_value("N_stat"))):
        instrument_c.voltage = float(vlim)
        instrument_c.current = -float(i_bias)
        instrument_c.operate = True
        time.sleep(0.1)
        med_v = instrument_v.voltage_dc
        if np.abs(float(med_v)) > 0.01:
            dpg.set_value("i_bias", float(i_bias)/10)
            instrument_c.operate = False
            time.sleep(0.1)
            pass
        elif np.abs(float(med_v)) < 0.001:
            dpg.set_value("i_bias", float(i_bias)*10)
            instrument_c.operate = False
            time.sleep(0.1)
            pass
        time.sleep(0.1)
        instrument_c.operate = False
        meas_v.append(med_v)
        sent_i.append(float(i_bias))
    v_mean = np.mean(meas_v)
    v_std = np.std(meas_v)
    return [v_mean, sent_i]
    #return [v_mean, v_std, i_bias]

with dpg.window(label="Keithley 224", width=w, height=120, pos=(0,130)):
    dpg.add_text("V-Limit", pos=(20,20))
    V_Limit = dpg.add_input_text(label="V", default_value=f"{1}", tag="vlim", width=40, pos=(20,40))
    dpg.add_text("N mediciones", pos=(20, 60))
    N_stat = dpg.add_input_text(default_value=f"{3}", tag="N_stat", width=40, pos=(20,80))
    dpg.add_text("Corriente bias", pos=(150, 20))
    i_bias = dpg.add_input_text(label="A", default_value=f"{0.00001}", tag="i_bias", width=60, pos=(150,40))

with dpg.window(label="LakeShore 340", width=w, height=140, pos=(0,250)):
    P = dpg.add_input_text(default_value=f"{dpg.get_value("P_m")}", width=40, tag="P_in", pos=(20,40))
    dpg.add_text("P", pos=(20,20))
    I = dpg.add_input_text(default_value=f"{dpg.get_value("I_m")}", width=40, tag="I_in", pos=(140,40))
    dpg.add_text("I", pos=(150,20))
    D = dpg.add_input_text(default_value=f"{dpg.get_value("D_m")}", width=40,tag="D_in", pos=(270,40))
    dpg.add_text("D", pos=(270,20))
    T_est = dpg.add_input_text(default_value=f"60", width=40,tag="T_est", pos=(20,82))
    dpg.add_text("Tiempo estable (s)", pos=(20,62))
    heater_display_text = dpg.add_input_text(default_value=f"{dpg.get_value("HR_m")}", tag="HR_in", pos=(240, 79))
    dpg.add_text("Heater Range", pos=(240, 79))


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
                        borders_innerV=True, borders_outerV=True, height = 200, no_host_extendY = True,
                        scrollY = True, parent="g_col"):
            dpg.add_table_column(label="T (K)")
            dpg.add_table_column(label="Rate (K/min)")
            dpg.add_table_column(label="Estable?")

def crea_tablas_H(sender, app_data, user_data):
    H0 = float(dpg.get_value("H0"))
    HF = float(dpg.get_value("HF")) if (float(dpg.get_value("HF")) < 9) else 9
    sepH = float(dpg.get_value("sepH"))
    N = int(np.abs(H0-HF)/sepH) + 1
    hes = np.round(np.linspace(H0, HF, N),1)
    data_row = [hes, np.full_like(hes, 1)]
    for i in range(0, N):
            with dpg.table_row(parent="Tabla_H"):
                for j in range(0, 2):
                    dpg.add_input_text(default_value=f"{data_row[j][i]}")

def reset_table_H(sender, app_data, user_data):
    dpg.delete_item("Tabla_H", children_only= False)
    with dpg.table(header_row=True, tag="Tabla_H", borders_innerH=True, borders_outerH=True,
                        borders_innerV=True, borders_outerV=True, height = 150, no_host_extendY = True,
                        scrollY = True, parent="g_col_H"):
            dpg.add_table_column(label="Campo (H)")
            dpg.add_table_column(label="Medir?")

def medicion_H(sender, app_data, user_data):
    try:
        dpg.remove_alias("tl")
        dpg.remove_alias("sl")
        dpg.remove_alias("rl")
        dpg.remove_alias("pl")
        dpg.remove_alias("r1l")
        dpg.remove_alias("r2l")
        dpg.remove_alias("sl")
        dpg.remove_alias("pl")
        dpg.remove_alias("if")
        dpg.remove_alias("vb")
        dpg.remove_alias("hel")
        dpg.remove_alias("ttl")
        dpg.remove_alias("ttal")
        dpg.remove_alias("tal")
    except SystemError:
        pass
    with dpg.window(label="Control en vivo", width=w, height=260, pos=(0,390)):
        dpg.add_text("T actual (K)", pos=(10,20))
        t_actual_display = dpg.add_text("0.00 K", tag="tl", pos=(10,40))
        dpg.add_text("T setpoint (K)", pos=(115,20))
        setp_actual_display = dpg.add_text("0.00 K", tag="sl", pos=(115,40))
        dpg.add_text("Potencia (%)", pos=(235,20))
        pot_actual_display = dpg.add_text("0.00 %", tag="pl", pos=(235,40))
        dpg.add_text("I fuente (A)", pos=(10,60))
        ib_actual_display = dpg.add_text("0 A", tag="if", pos=(10,80))
        dpg.add_text("V bobina (V)", pos=(115,60))
        if_actual_display = dpg.add_text("0 V", tag="vb", pos=(115,80))
        dpg.add_text("Campo est. (T)", pos=(235,60))
        hest_actual_display = dpg.add_text("0 G", tag="hel", pos=(235,80))
        dpg.add_text("R muestra 1", pos=(10,100))
        r1_actual_display = dpg.add_text("0.00E+0 Ohm", tag="r1l", pos=(10,120))
        dpg.add_text("R muestra 2", pos=(115,100))
        r2_actual_display = dpg.add_text("0.00E+0 Ohm", tag="r2l", pos=(115,120))
        dpg.add_text("Tiempo total", pos=(10,140))
        ttal_actual_display = dpg.add_text("00:00:00", tag="ttl", pos=(10,160))
        dpg.add_text("Tiempo tarea", pos=(115,140))
        tact_actual_display = dpg.add_text("00:00:00", tag="ttal", pos=(115,160))
        dpg.add_text("Tarea actual", pos=(10,200))
        tar_actual_display = dpg.add_text("AFK", tag="tal", pos=(10,220))
        medir_tabla_T_en_H()

def update_vars(): #esta funcion lee los parametros puestos en la ventana y los actualiza en vivo con el multithread
    controller = LakeShore340(gpib_address=12)
    instrument_c = k224.KEITHLEY_224("GPIB0::2::INSTR")
    instrument_c.voltage = float(dpg.get_value("vlim"))
    controller.write(f'PID 1, {dpg.get_value("P_in")}, {dpg.get_value("I_in")}, {dpg.get_value("D_in")}')
    controller.write(f'RANGE 1, {dpg.get_value("HR_in")}')
    controller.close()
    np.savetxt('configls.txt', [f'{dpg.get_value("P_in")}, {dpg.get_value("I_in")}, {dpg.get_value("D_in")}, {dpg.get_value("HR_in")}'], fmt='%s')

t_plot = []
T_plot = []
Ts_plot = []
Pot_plot = []
r1_plot = []
r2_plot = []
Ib_plot = []

def ramp_T(T, rate):
    dpg.set_value('tal', "Rampa de temperatura")
    update_vars()
    t0 = time.time()
    t_report = 0
    controller = LakeShore340(gpib_address=12)
    current_setpoint = controller.get_setpoint()
    target_setpoint = T
    if target_setpoint > current_setpoint:
        rate = -float(rate)
    rampa = np.arange(float(current_setpoint), float(target_setpoint), float(rate)/30)
    print(current_setpoint, target_setpoint, rate, rampa)
    rampa[-1] = target_setpoint
    for i in rampa:
        update_vars()
        controller.set_setpoint(i)
        lecturas()
        time.sleep(2)
        t_report = time.time()-t0
        dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t_report)))
        t_tot = time.time()-tiempo_total
        dpg.set_value('ttl', time.strftime("%H:%M:%S", time.gmtime(t_tot)))

def ramp_H(I_actual, I):
    update_vars()
    t0 = time.time()
    t = 0
    dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
    fuente = LakeShore625('GPIB0::11::INSTR')
    fuente.limit(60, 3, 0.17) #algunos limites a nivel software
    fuente.write('PSHS 1 55 10') #parametros del switch
    controller = LakeShore340(gpib_address=12)
    fuente.set_voltage(2.5) #por las dudas vuelvo a poner el limite de Cryo
    fuente.set_ramp_rate(0.15) #le pongo la velocidad a la fuente
    fuente.set_current(I_actual) #pongo la ultima corriente registrada en la bobina
    dpg.set_value('tal', "Subiendo corriente sin switch")
    while fuente.get_status_ramp() == 0: #espero a que haga su rampa
        I_real = fuente.get_current()
        update_vars()
        lecturas()
        if (I_real-I_actual) < 0.01:
            break
        time.sleep(1)
        t = time.time()-t0
        dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
        t_tot = time.time()-tiempo_total
        dpg.set_value('ttl', time.strftime("%H:%M:%S", time.gmtime(t_tot)))
    fuente.psh(1) #prendo el switch persistente
    dpg.set_value('tal', "Esperando conexión del switch")
    while fuente.get_status_switch() != 1.0:
        t = time.time()-t0
        dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
        t_tot = time.time()-tiempo_total
        dpg.set_value('ttl', time.strftime("%H:%M:%S", time.gmtime(t_tot)))
        update_vars()
        lecturas()
        time.sleep(1)
    fuente.set_current(I)
    fuente.get_status_ramp()
    while fuente.get_status_ramp() == 0.0:
        dpg.set_value('tal', "Subiendo corriente de la bobina")
        update_vars()
        lecturas()
        time.sleep(1)
        t = time.time()-t0
        dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
        t_tot = time.time()-tiempo_total
        dpg.set_value('ttl', time.strftime("%H:%M:%S", time.gmtime(t_tot)))
    fuente.psh(0) #apago el switch una vez que llegue a la corriente necesaria
    while fuente.get_status_switch() != 0.0:
        dpg.set_value('tal', "Esperando desconexión del switch")
        t = time.time()-t0
        dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
        t_tot = time.time()-tiempo_total
        dpg.set_value('ttl', time.strftime("%H:%M:%S", time.gmtime(t_tot)))
        update_vars()
        lecturas()
        time.sleep(1)
    I_act = fuente.get_current_psh()
    fuente.set_current(0)
    fuente.get_status_ramp()
    while fuente.get_status_ramp() == 0.0:
        dpg.set_value('tal', "Apagando corriente sin switch")
        t = time.time()-t0
        dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
        t_tot = time.time()-tiempo_total
        dpg.set_value('ttl', time.strftime("%H:%M:%S", time.gmtime(t_tot)))
        lecturas()
        update_vars()
        time.sleep(1)
    dpg.set_value("I_actual", I_act) #guardo la ultima corriente enviada para cuando vuelva a encender el switch

tiempo_total = time.time()

def medir_tabla_T_en_H():
    update_vars()
    tiempo_start = time.time() #pongo tiempos iniciales y levanto las listas que se van a medir
    tiempo_est = 0
    final_T = 0
    final_H = 0
    controller = LakeShore340(gpib_address=12)
    algo_T = dpg.get_item_children("Tabla", 1)
    algo_H = dpg.get_item_children("Tabla_H", 1)
    for fila in algo_T: #en cada temperatura corro el protocolo estabilizar y barrer campos
        parametros_T = dpg.get_item_children(fila, 1)
        update_vars() #estos updates sirven por si se actualizan parametros del PID, heater o medición
        setpoint = dpg.get_value(parametros_T[0])
        final_T = dpg.get_value(parametros_T[0])
        rate = dpg.get_value(parametros_T[1])
        ramp_T(setpoint, rate) #esto lleva la temperatura en rampa (ver ramp_T)
        T_real = controller.read_temperature(1)
        tiempo_est = time.time()
        while abs(T_real-setpoint) > setpoint*0.01: #mientras la diferencia es mayor a un porcentaje del setpoint no hace nada
            estable = dpg.get_value(parametros_T[2])
            update_vars()
            dpg.set_value("tal", "Esperando llegada al setpoint")
            lecturas() #esta funcion va a leer el Lakeshore, el nanovoltimetro y la fuente de alta corriente y va a guardar los datos
            tiempo_est = time.time()-tiempo_start
            tiempo_tot = time.time()-tiempo_start
            dpg.set_value("ttl", tiempo_tot) #esto actualiza un tiempo para diagnostico, no representa lo guardado (tiempo real)
            dpg.set_value("ttal", tiempo_est)
            if dpg.get_value(estable == '0' or estable == '0.00'): #esto es por si se quiere saltear este punto
                break
            time.sleep(2)
        while True: #una vez que se va abajo del threshold intenta estabilizar por x segundos
            estable = dpg.get_value(parametros_T[2])
            update_vars()
            dpg.set_value("tal", "Estabilizando...")
            lecturas()
            tiempo_est = time.time()-tiempo_start
            tiempo_tot = time.time()-tiempo_start
            dpg.set_value("ttl", tiempo_tot)
            dpg.set_value("ttal", tiempo_est)
            T_real = controller.read_temperature(1) #acá abajo dice que si la diferencia es mayor a un porcentaje, empiece a contar otra vez
            if abs(T_real-setpoint) > setpoint*0.01:#si es menor al porcentaje sigue contando, y si es menor y ya conto suficiente pare la
                tiempo_est = 0                      #estabilización
            if tiempo_est < float(dpg.get_value("T_est")):
                pass
            elif tiempo_est >= float(dpg.get_value("T_est")):
                break
            elif (estable == 0 or estable == 0.00): #idem arriba por si se quiere saltar
                break
        for filah in algo_H: #acá va a barrer campos para cada temperatura dada
            parametros_H = dpg.get_item_children(filah, 1)
            setpoint_H = dpg.get_value(parametros_H[0])
            update_vars()
            ramp_H(float.get_value('I_actual'), setpoint_H/1191.4)
            for i in np.arange(1,int(dpg.get_value("ctd_msr"))): #hago muchas lecturas en cada campo, no se si es necesario
                lecturas()
            final_H = setpoint_H
    ramp_H(final_H, 0) #vuelvo el campo a 0 con el mismo protocolo
    ramp_T(final_T, 295, 2) #vuelvo la temperatura a ambiente con el mismo protocolo

with dpg.window(label="Medición T", width=370, height=650, pos=(w,0)):
    T0m = dpg.add_input_text(default_value=f"{295}", width=40, tag="T0", pos=(20,40))
    dpg.add_text("T inicial (K)", pos=(20,20))
    Tm = dpg.add_input_text(default_value=f"{100}", width=40, tag="TF", pos=(150,40))
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
                        borders_innerV=True, borders_outerV=True, height = 200, no_host_extendY = True,
                        scrollY = True):
            dpg.add_table_column(label="T (K)")
            dpg.add_table_column(label="Rate (K/min)")
            dpg.add_table_column(label="Estable?")
    dpg.add_button(label="Limpiar", callback=reset_table_T, pos=(20,330))
    H0m = dpg.add_input_text(default_value=f"{0}", width=40, tag="H0", pos=(20,380))
    dpg.add_text("H inicial (G)", pos=(20,360))
    Hm = dpg.add_input_text(default_value=f"{0.1}", width=40, tag="HF", pos=(150,380))
    dpg.add_text("H final (G)", pos=(150,360))
    Hsepm = dpg.add_input_text(default_value=f"{0.1}", width=40,tag="sepH", pos=(270,380))
    dpg.add_text("dH (G)", pos=(270,360))
    N_mediciones = dpg.add_input_text(default_value=f'{5}', width = 40, tag="ctd_msr", pos=(20,430))
    dpg.add_text("# mediciones(/2)", pos=(20,410))
    dpg.add_button(label="Agregar", callback=crea_tablas_H, pos=(270,410))
    with dpg.group(tag="g_col_H", pos=(10,460)):
        with dpg.table(header_row=True, tag="Tabla_H", borders_innerH=True, borders_outerH=True,
                        borders_innerV=True, borders_outerV=True, height = 150, no_host_extendY = True,
                        scrollY = True):
            dpg.add_table_column(label="H (T)")
            dpg.add_table_column(label="Medir?")
    dpg.add_button(label="Limpiar", callback=reset_table_H, pos=(20,620))
    dpg.add_button(label="Comenzar", callback=medicion_H, pos=(270,620))

with dpg.window(label='Temperatura', pos=(w+370,0)):
    with dpg.plot(height=250, width=300):
            dpg.add_plot_axis(dpg.mvXAxis, label="Tiempo (s)", tag="t_temp_ax")
            dpg.add_plot_axis(dpg.mvYAxis, label="Temperatura (K)", tag="T_setp_y")
            dpg.add_line_series([], [], label="T Setpoint", parent="t_temp_ax", tag="T_setp_p")
            dpg.add_line_series([], [], label="T Actual", parent="t_temp_ax", tag="T_act_p")
            dpg.add_plot_axis(dpg.mvYAxis, label="Potencia (%)", tag="Pot_y")
            dpg.add_line_series([], [], label="Potencia", parent="t_temp_ax", tag="Pot_p")

with dpg.window(label='Muestra', pos=(w+370,285)):
    with dpg.plot(height=250, width=300):
            dpg.add_plot_axis(dpg.mvXAxis, label="Tiempo (s)", tag="t_temp_ax_m")
            dpg.add_plot_axis(dpg.mvYAxis, label="Resistencia (Ohm)", tag="Res_y")
            dpg.add_line_series([], [], label="Muestra 1", parent="t_temp_ax_m", tag="r_1_p")
            dpg.add_line_series([], [], label="Muestra 2", parent="t_temp_ax_m", tag="r_2_p")
            #dpg.add_plot_axis(dpg.mvYAxis, label="Resistencia (Ohm)", tag="Res_y")
            #dpg.add_line_series([], [], label="Potencia", parent="t_temp_ax", tag="Pot_p")

with dpg.window(label='Campo', pos=(w+370+315,0)):
    with dpg.plot(height=250, width=300):
            dpg.add_plot_axis(dpg.mvXAxis, label="Tiempo (s)", tag="t_temp_ax_c")
            dpg.add_plot_axis(dpg.mvYAxis, label="Corriente (A)", tag="Curr_y")
            dpg.add_line_series([], [], label="Corriente", parent="t_temp_ax_c", tag="H_p")
            dpg.add_plot_axis(dpg.mvYAxis, label="Campo (G)", tag="H_y")
            #dpg.add_line_series([], [], label="Potencia", parent="t_temp_ax_c", tag="Pot_p")


#with dpg.window(label='I bias', pos=(w+370,0)):
#    with dpg.plot(label="I vs N Plot", height=250, width=250):
#            dpg.add_plot_axis(dpg.mvXAxis, label="N", tag="NI_axis")
#            dpg.add_plot_axis(dpg.mvYAxis, label="I", tag="I_axis")
#            dpg.add_line_series([], [], label="Series 1", parent="I_axis", tag="c_plot")

#with dpg.window(label='V bias', pos=(w+370+250+15,0)):
#    with dpg.plot(label="V vs N", height=250, width=250):
#            dpg.add_plot_axis(dpg.mvXAxis, label="N", tag="NV_axis")
#            dpg.add_plot_axis(dpg.mvYAxis, label="V", tag="V_axis")
#            dpg.add_line_series([], [], label="Series V", parent="V_axis", tag="v_plot")

#with dpg.window(label='R calc', pos=(w+370,280)):
#    with dpg.plot(label="R vs I", height=250, width=250):
#            dpg.add_plot_axis(dpg.mvXAxis, label="I", tag="IR_axis")
#            dpg.add_plot_axis(dpg.mvYAxis, label="R", tag="R_axis")
#            dpg.add_line_series([], [], label="Series R", parent="R_axis", tag="r_plot")


dpg.setup_dearpygui()
dpg.maximize_viewport()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()