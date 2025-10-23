# -*- coding: utf-8 -*-
"""
Created on Wed Mar 12 12:16:47 2025

@author: Charly
"""
#%%
import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt

def duffing_equations_dc(y, t, gamma, alpha, beta, F_ac, omega, F_dc):
    """
    y[0] = x(t)
    y[1] = v(t) = dx/dt
    
    Ecuaciones de Duffing con fuerza AC (F_ac*cos(omega*t)) y DC (F_dc).
    """
    x, v = y
    dxdt = v
    dvdt = -gamma*v - alpha*x - beta*x**3 + F_ac*np.cos(omega*t) + F_dc
    return [dxdt, dvdt]

def simulate_duffing_dc(gamma=0.1, alpha=-1.0, beta=1.0,
                        F_ac=0.0, omega=1.0, F_dc=0.0,
                        x0=-0.5, v0=0.0,
                        tmax=200, dt=0.01):
    """
    Integra la ecuación de Duffing con término DC.
    Retorna el vector de tiempos y la solución (x(t), v(t)).
    """
    # Vector de tiempos
    t = np.arange(0, tmax, dt)
    
    # Condiciones iniciales
    y0 = [x0, v0]
    
    # Integrar
    sol = odeint(duffing_equations_dc, y0, t,
                 args=(gamma, alpha, beta, F_ac, omega, F_dc))
    
    return t, sol

def plot_time_series(t, sol, title=''):
    """
    Grafica x(t) y v(t).
    """
    x = sol[:, 0]
    v = sol[:, 1]

    plt.figure()
    plt.plot(t, x, label='x(t)')
    #plt.plot(t, v, label='v(t)')
    plt.xlabel('Tiempo')
    plt.ylabel('Amplitud')
    plt.title(title)
    plt.legend()
    plt.show()

def plot_phase_space(sol, w, t=None):
    """
    Grafica el diagrama de espacio fase (v vs x) con colormap basado en el tiempo.
    """
    x = sol[:, 0]
    v = sol[:, 1]
    if t is None:
        t = np.arange(len(x))
    # Normalize t for colormap
    t_norm = (t - np.min(t)) / (np.max(t) - np.min(t))
    # plt.figure()
    sc = plt.scatter(x, v, s=2, label=f'{w}')
    # plt.show()

def main():
    """
    1) Exploración de la transición al variar F_dc (control DC).
    2) Exploración de la frecuencia crítica al variar omega.
    """
    # plt.close('all')
    
    # Parámetros fijos (disipación y potencial)
    gamma = 0.1
    alpha = -1.0
    beta = 0.25
    
    # Elegimos una amplitud AC y la variamos después si queremos
    F_ac1 = 0.2
    
    # --- 1) Variación en F_dc ---
    #    Manteniendo F_ac y omega constantes, veamos cómo cambia la dinámica.
    dc_values = [-2, -1, -0.5, 0.0]
    omega_fixed = 1.0
    
    # for fdc in dc_values:
    #     t, sol = simulate_duffing_dc(gamma=gamma, alpha=alpha, beta=beta,
    #                                  F_ac=F_ac1, omega=omega_fixed, F_dc=fdc,
    #                                  x0=0.1, v0=0.0,
    #                                  tmax=200, dt=0.01)
    #     title_time = f'Duffing DC: F_ac={F_ac1}, omega={omega_fixed}, F_dc={fdc}'
    #     # plot_time_series(t, sol, title=title_time)
    #     plot_phase_space(sol, title=title_time)

    # --- 2) Exploración de la frecuencia crítica al variar omega ---
    #    Fijamos un F_dc > 0 (un valor que genere la inclinación de potencial)
    F_dc_chosen = -0.1
    omegas = np.round(np.geomspace(0.5, 2, 4),3 )
    F_ac2 = 0.4 
    
    for w in omegas:
        t, sol = simulate_duffing_dc(gamma=gamma, alpha=alpha, beta=beta,
                                     F_ac=F_ac2, omega=w, F_dc=F_dc_chosen,
                                     x0=0, v0=0.0,
                                     tmax=200, dt=0.01)
        # plot_time_series(t, sol, title=title_time)
        plot_phase_space(sol[:], w)
    plt.legend()
    plt.xlabel('x')
    plt.ylabel('v = dx/dt')
if __name__ == '__main__':
    main()


#%%

# Parámetros fijos
gamma = 0.1
alpha = -1.0
beta = 0.25
F_ac = 0.4       # algo moderado con 0.3 RS de -2 a +2; con 0.4 de +2 a -2
F_dc = -0.1       # inclinación moderada #con +0.1 se da lo de arriba. #con -0.1 trnasiciona con F_ac=0.4 de - a +
tmax = 200
dt = 0.01

# Rangos de frecuencia
omega_vals = np.geomspace(0.5, 4, 20)

# Inicializamos condiciones
x0 = 0.0
v0 = 0.0

amplitud_final = []
x_sol_final = []

for w in omega_vals:
    # Integra con las condiciones iniciales actuales
    t = np.arange(0, tmax, dt)
    y0 = [x0, v0]
    sol = odeint(duffing_equations_dc, y0, t, 
                 args=(gamma, alpha, beta, F_ac, w, F_dc))
    
    # Toma la parte final de la solución
    x_sol = sol[:,0]
    v_sol = sol[:,1]
    
    # Mide la amplitud, por ejemplo la diferencia entre max y min
    # en la parte final de la simulación
    x_final = x_sol[int(0.8*len(x_sol)):]  # 80% al 100% del tiempo
    amp = np.max(x_final) - np.min(x_final)
    amplitud_final.append(amp)
    
    
    # Actualiza condiciones iniciales para la próxima freq
    x0 = x_sol[-1]
    v0 = v_sol[-1]
    x_sol_final.append(x0)


plt.close('all')
# Grafica amplitud vs. frecuencia
plt.figure(1)
plt.plot(omega_vals, amplitud_final, 'o-')
plt.xlabel('Frecuencia ω')
plt.ylabel('Amplitud (máx-min en régimen estacionario)')
plt.title('Barrido en frecuencia y respuesta estacionaria')
plt.show()

plt.figure(2)
plt.plot(omega_vals, x_sol_final, 'o-')
plt.xlabel('Frecuencia ω')
plt.ylabel('Posición final')
plt.title('Barrido en frecuencia y respuesta estacionaria')
plt.show()