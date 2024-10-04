import numpy as np
import time
import dearpygui as dpg
from ls625 import *
from ls340 import *


def ramp_H(I_actual, I):
    t0 = time.time()
    t = 0
    print(time.strftime("%H:%M:%S", time.gmtime(t)))
    #dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
    fuente = LakeShore625('GPIB0::11::INSTR')
    fuente.limit(60, 3, 0.17)
    fuente.write('PSHS 1 55 10')
    fuente.status_ramp()
    controller = LakeShore340(gpib_address=12)
    fuente.set_voltage(3) #por las dudas vuelvo a poner el limite de Cryo
    fuente.set_ramp_rate(0.17)
    fuente.set_current(I_actual) #pongo la ultima corriente registrada en la bobina (hay que mejorar esto para que sea mas fiable)
    while fuente.get_status_ramp() == 0.0: #por las dudas me fijo que este dentro de buenos margenes de igualdad, quizas no sea necesario
        #update_vars()
        #lecturas()
        t = time.time()-t0
        print(time.strftime("%H:%M:%S", time.gmtime(t)))
        time.sleep(1)
        #dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
    #fuente.psh(1) #prendo el switch persistente
    time.sleep(10) #le doy un ratito para que normalice (quizas haya que mejorar esto)
    t = time.time()-t0
    print(time.strftime("%H:%M:%S", time.gmtime(t)))
    #dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
    fuente.set_current(I)
    while fuente.status() != 1:
        #update_vars()
        #lecturas()
        time.sleep(1)
        t = time.time()-t0
        print(time.strftime("%H:%M:%S", time.gmtime(t)))
        #dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
    #fuente.psh(0) #apago el switch una vez que llegue a la corriente necesaria
    #while fuente.status() != 1:
    #    t = time.time()-t0
    #    dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
    #    time.sleep(1)
    #I_act = fuente.get_current_psh()
    fuente.set_current(0)
    while fuente.status() != 1:
        t = time.time()-t0
        print(time.strftime("%H:%M:%S", time.gmtime(t)))
        #dpg.set_value('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
        time.sleep(1)
    #dpg.set_value("I_actual", I_act) #guardo la ultima corriente enviada para cuando vuelva a encender el switch
