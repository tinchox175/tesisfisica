def ramp_H(I_actual, I):
    t0 = time.time()
    t = 0
    dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
    fuente = LakeShore625('GPIB0::11::INSTR')
    fuente.limit(60, 3, 0.17)
    fuente.write('PSHS 1 55 10')
    controller = LakeShore340(gpib_address=12)
    fuente.set_voltage(3) #por las dudas vuelvo a poner el limite de Cryo
    fuente.set_current(I_actual) #pongo la ultima corriente registrada en la bobina (hay que mejorar esto para que sea mas fiable)
    while True: #por las dudas me fijo que este dentro de buenos margenes de igualdad, quizas no sea necesario
        I_real = fuente.get_current()
        update_vars()
        lecturas()
        if (I_real-I_actual) < 0.01:
            break
        time.sleep(2)
        t = time.time()-t0
        dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
    fuente.psh(1) #prendo el switch persistente
    time.sleep(10) #le doy un ratito para que normalice (quizas haya que mejorar esto)
    t = time.time()-t0
    dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
    rampa = np.arange(I_actual, I, 0.15) #armo la rampa de corrientes hasta la del campo pedido
    for i in rampa:
        fuente.set_current(i)
        update_vars()
        lecturas()
        time.sleep(1.5)
        t = time.time()-t0
        dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
    fuente.psh(0) #apago el switch una vez que llegue a la corriente necesaria
    time.sleep(10)
    t = time.time()-t0
    dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
    I_act = fuente.get_current()
    rampa_off = np.arange(I_act, 0, 0.05)
    for j in rampa_off:
        fuente.set_current(j)
        while float(fuente.get_voltage()) > 0.5:
            time.sleep(1)
            t = time.time()-t0
            dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
    fuente.set_current(0) #apago la corriente de la fuente (una vez que el switch esta apagado)
    dpg.set_value("I_actual", I_act) #guardo la ultima corriente enviada para cuando vuelva a encender el switch
