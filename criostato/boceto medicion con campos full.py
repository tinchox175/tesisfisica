import numpy as np
import dearpygui as dpg
import time

def update_vars():
    controller = LakeShore340(gpib_address=12)
    instrument_c = k224.KEITHLEY_224("GPIB0::2::INSTR")
    instrument_c.voltage = float(dpg.get_value("vlim"))
    controller.write(f'PID 1, {dpg.get_value("P_in")}, {dpg.get_value("I_in")}, {dpg.get_value("D_in")}')
    controller.write(f'RANGE 1, {dpg.get_value("HR")}')
    controller.close()
    np.savetxt('configls.txt', [f'{dpg.get_value("P_in")}, {dpg.get_value("I_in")}, {dpg.get_value("D_in")}, {dpg.get_value("HR")}'], fmt='%s')

def lecturas():
    data_ls = [controller.read_temperature(1), controller.get_setpoint(1), controller.query('HTR?')]
    dpg.set_value("T_actual", data_ls[0])
    dpg.set_value("T_setpoint", data_ls[1])
    dpg.set_value("Pwr", data_ls[2])
    data_r = [N_stat_msr]
    dpg.set_value("r1l", data_r[0]/data_r[1])
    data_b = [I_bob, fuente.read_V, fuente.read_I, 1.1914*float(fuente.read_I)]
    add_row([time.strftime("%H %M %S", time.localtime()), data_ls[0], data_ls[1], data_ls[2], data_r[0], data_r[1], data_r[0]/data_r[1], data_b[0], data_b[1], data_b[2]], 1)

def ramp_T(T, rate):
    current_setpoint = controller.get_setpoint()
    target_setpoint = T
    rampa = np.arange(current_setpoint, target_setpoint, rate/30)
    for i in rampa:
        controller.set_setpoint(i)
        time.sleep(2)
    return tiempo

def ramp_H(I_actual, I):
    fuente.set_voltage(3)
    fuente.set_current(I_actual)
    while True:
        I_real = fuente.read_current()
        if (I_real-H_actual) < 0.01:
            break
    controller.analog_out(100)
    time.sleep(5)
    rampa = np.arange(I_actual, I, 0.1)
    for i in rampa
        fuente.set_current(i)
        time.sleep(1.5)
    controller.analog_out(0)
    return I

def medir_tabla_T_en_H(algo_T, algo_H):
    tiempo_start = time.time()
    tiempo_tot = 0
    lista_T, rate = algo_T
    lista_H = algo_H
    controller = LakeShore340(gpib_address=12)
    for setpoint in lista_T:
        update_vars()
        tiempo_est = ramp_T(setpoint, rate)
        T_real = controller.read_temperature(1)
        tiempo_est = time.time()
        while abs(T_real-setpoint) > setpoint*0.01:
            update_vars()
            dpg.set_value("tal", "Yendo al setpoint")
            lecturas()
            tiempo_est = time.time()-tiempo_start
            tiempo_tot = time.time()-tiempo_start
            dpg.set_value("ttl", tiempo_tot)
            dpg.set_value("ttal", tiempo_est)
            if dpg.get_value(estable == '0' or estable == '0.00'):
                break
            time.sleep(2)
        while True:
            update_vars()
            dpg.set_value("tal", "Estabilizando...")
            data_ls = [controller.read_temperature(1), controller.get_setpoint(1), controller.query('HTR?')]
            dpg.set_value("T_actual", data_ls[0])
            dpg.set_value("T_setpoint", data_ls[1])
            dpg.set_value("Pwr", data_ls[2])
            data_r = [N_stat_msr]
            dpg.set_value("r1l", data_r[0]/data_r[1])
            add_row([time.strftime("%H %M %S", time.localtime()), data_ls[0], data_ls[1], data_ls[2], data_ls[3], data_r[0], data_r[1], data_r[0]/data_r[1]], 1)
            tiempo_est = time.time()-tiempo_start
            tiempo_tot = time.time()-tiempo_start
            dpg.set_value("ttl", tiempo_tot)
            dpg.set_value("ttal", tiempo_est)
            T_real = controller.read_temperature(1)
            if abs(T_real-setpoint) > setpoint*0.01:
                tiempo_est = 0
            if tiempo_est < float(dpg.get_value("T_est")):
                pass
            elif tiempo_est >= float(dpg.get_value("T_est")):
                break
            elif (estable == 0 or estable == 0.00):
                break
            time.sleep(2)
    for setpoint in lista_T:
        update_vars()
        tiempo_est = ramp_T(setpoint, rate)
        