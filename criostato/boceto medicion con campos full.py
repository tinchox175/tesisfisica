import numpy as np
import dearpygui as dpg
import time

def update_vars(): #esta funcion lee los parametros puestos en la ventana y los actualiza en vivo con el multithread
    controller = LakeShore340(gpib_address=12)
    instrument_c = k224.KEITHLEY_224("GPIB0::2::INSTR")
    instrument_c.voltage = float(dpg.get_value("vlim"))
    controller.write(f'PID 1, {dpg.get_value("P_in")}, {dpg.get_value("I_in")}, {dpg.get_value("D_in")}')
    controller.write(f'RANGE 1, {dpg.get_value("HR")}')
    controller.close()
    np.savetxt('configls.txt', [f'{dpg.get_value("P_in")}, {dpg.get_value("I_in")}, {dpg.get_value("D_in")}, {dpg.get_value("HR")}'], fmt='%s')

def lecturas(): #esta funcion lee los aparatos y guarda todo lo que lee en el registro final
    data_ls = [controller.read_temperature(1), controller.get_setpoint(1), controller.query('HTR?')]
    dpg.set_value("tl", data_ls[0])
    dpg.set_value("sl", data_ls[1])
    dpg.set_value("pl", data_ls[2])
    data_r = [N_stat_msr]
    dpg.set_value("r1l", data_r[0]/data_r[1])
    dpg.set_value("r2l", data_r[2]/data_r[3])
    data_b = [I_bob, fuente.read_V, fuente.read_I, 1.1914*float(fuente.read_I)]
    dpg.set_value("ib", data_b[0])
    dpg.set_value("vb", data_b[1])
    dpg.set_value("if", data_b[2])
    dpg.set_value("hel", data_b[3])
    add_row([time.strftime("%H %M %S", time.localtime()), data_ls[0], data_ls[1], data_ls[2], data_r[0], data_r[1], data_r[0]/data_r[1], data_r[2]/data_r[3], data_b[0], data_b[1], data_b[2], data_b[3]], 1)

def ramp_T(T, rate):
    current_setpoint = controller.get_setpoint()
    target_setpoint = T
    rampa = np.arange(current_setpoint, target_setpoint, rate/30)
    for i in rampa:
        update_vars()
        controller.set_setpoint(i)
        lecturas()
        time.sleep(2)
    return tiempo

def ramp_H(I_actual, I):
    fuente.set_voltage(3) #por las dudas vuelvo a poner el limite de Cryo
    fuente.set_current(I_actual) #pongo la ultima corriente registrada en la bobina (hay que mejorar esto para que sea mas fiable)
    while True: #por las dudas me fijo que este dentro de buenos margenes de igualdad, quizas no sea necesario
        I_real = fuente.read_current()
        update_vars()
        lecturas()
        if (I_real-H_actual) < 0.01:
            break
        time.sleep(2)
    controller.analog_out(100) #prendo el switch persistente
    time.sleep(5) #le doy un ratito para que normalice (quizas haya que mejorar esto)
    rampa = np.arange(I_actual, I, 0.1) #armo la rampa de corrientes hasta la del campo pedido
    for i in rampa:
        fuente.set_current(i)
        update_vars()
        lecturas()
        time.sleep(1.5)
    controller.analog_out(0) #apago el switch una vez que llegue a la corriente necesaria
    time.sleep(5)
    I = fuente.get_current()
    fuente.set_current(0) #apago la corriente de la fuente (una vez que el switch esta apagado)
    return I #guardo la ultima corriente enviada para cuando vuelva a encender el switch

def medir_tabla_T_en_H(algo_T, algo_H):
    tiempo_start = time.time() #pongo tiempos iniciales y levanto las listas que se van a medir
    tiempo_tot = 0
    lista_T, rate = algo_T
    lista_H = algo_H
    controller = LakeShore340(gpib_address=12)
    for setpoint in lista_T: #en cada temperatura corro el protocolo estabilizar y barrer campos
        update_vars() #estos updates sirven por si se actualizan parametros del PID, heater o medición
        tiempo_est = ramp_T(setpoint, rate) #esto lleva la temperatura en rampa (ver ramp_T)
        T_real = controller.read_temperature(1)
        tiempo_est = time.time()
        while abs(T_real-setpoint) > setpoint*0.01: #mientras la diferencia es mayor a un porcentaje del setpoint no hace nada
            update_vars()
            dpg.set_value("tal", "Yendo al setpoint")
            lecturas() #esta funcion va a leer el Lakeshore, el nanovoltimetro y la fuente de alta corriente y va a guardar los datos
            tiempo_est = time.time()-tiempo_start
            tiempo_tot = time.time()-tiempo_start
            dpg.set_value("ttl", tiempo_tot) #esto actualiza un tiempo para diagnostico, no representa lo guardado (tiempo real)
            dpg.set_value("ttal", tiempo_est)
            if dpg.get_value(estable == '0' or estable == '0.00'): #esto es por si se quiere saltear este punto
                break
            time.sleep(2)
        while True: #una vez que se va abajo del threshold intenta estabilizar por x segundos
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
        for setpoint in lista_H: #acá va a barrer campos para cada temperatura dada
            update_vars()
            tiempo_est = ramp_H(setpoint, rate)
            for i in ctd_stat: #hago muchas lecturas en cada campo, no se si es necesario
                lecturas()
    ramp_H(lista_H[-1], 0) #vuelvo el campo a 0 con el mismo protocolo
    ramp_T(lista_T[-1], 295, 2) #vuelvo la temperatura a ambiente con el mismo protocolo
