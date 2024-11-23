from ls340 import *
import numpy as np
from hp34970a import *
import time
from ls625 import *

tiempo_total = time.time()

def ramp_H(I_actual, I):
    t0 = time.time()
    t = 0
    fuente = Lakeshore625(11)
    fuente.limit(60, 3, 0.17) #algunos limites a nivel software
    fuente.write('PSHS 1 55 10') #parametros del switch
    fuente.set_voltage(3) #por las dudas vuelvo a poner el limite de Cryo
    fuente.set_ramp_rate(0.0001) #le pongo la velocidad a la fuente
    fuente.set_current(I_actual) #pongo la ultima corriente registrada en la bobina
    while fuente.get_status_ramp() == 0: #espero a que haga su rampa
        I_real = fuente.get_current()
        print(fuente.get_current(), fuente.get_voltage())
        if (I_real-I_actual) < 0.01:
            break
        time.sleep(1)
        t = time.time()-t0
        t_tot = time.time()-tiempo_total
        print(t, t_tot)
    fuente.psh(1) #prendo el switch persistente
    print('tal', "Esperando conexión del switch")
    while fuente.get_status_switch() != 1.0:
        print(fuente.get_current(), fuente.get_voltage())
        t = time.time()-t0
        t_tot = time.time()-tiempo_total
        print(t, t_tot)
        time.sleep(1)
    fuente.set_current(I)
    print(fuente.get_status_ramp())
    while fuente.get_status_ramp() == 0.0:
        print(fuente.get_status_ramp())
        print('tal', "Subiendo corriente de la bobina")
        print(fuente.get_current(), fuente.get_voltage())
        time.sleep(1)
        t = time.time()-t0
        print('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
        t_tot = time.time()-tiempo_total
        print('ttl', time.strftime("%H:%M:%S", time.gmtime(t_tot)))
    fuente.psh(0) #apago el switch una vez que llegue a la corriente necesaria
    while fuente.get_status_switch() != 0.0:
        print('tal', "Esperando desconexión del switch")
        t = time.time()-t0
        print('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
        t_tot = time.time()-tiempo_total
        print('ttl', time.strftime("%H:%M:%S", time.gmtime(t_tot)))
        print(fuente.get_current(), fuente.get_voltage())
        time.sleep(1)
    I_act = fuente.get_current_psh()
    fuente.set_current(0)
    print(fuente.get_status_ramp())
    while fuente.get_status_ramp() == 0.0:
        print(fuente.get_status_ramp())
        print('tal', "Apagando corriente sin switch")
        print(fuente.get_current(), fuente.get_voltage())
        t = time.time()-t0
        print('ttal', time.strftime("%H:%M:%S", time.gmtime(t)))
        t_tot = time.time()-tiempo_total
        print('ttl', time.strftime("%H:%M:%S", time.gmtime(t_tot)))
        time.sleep(1)
    print(I_act)
#ramp_H(0,0.001)