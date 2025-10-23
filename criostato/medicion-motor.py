import os
import os.path
import sys
import dearpygui.dearpygui as dpg # type: ignore
#import pymeasure.instruments.agilent as agi # type: ignore
import numpy as np # type: ignore
import time
test = 1 # 0 instrumentos reales, 1 mocks
if test == 0:
    import a34420a
    #import ls340
    import lsdrc91ca
    import agie3643a
    #import hp34970a
    import k224
    import csv
else:
    import a34420a_mock as a34420a
    #import ls340_mock as ls340
    import lsdrc91ca_mock as lsdrc91ca
    import agie3643a_mock as agie3643a
    #import hp34970a_mock as hp34970a
    import k224_mock as k224
    import csv
from decimal import Decimal
import threading
import queue
from collections import deque

# --- OBJETOS DE COMUNICACION THREAD-SAFE ---
results_queue = queue.Queue()
command_queue = queue.Queue()
stop_event = threading.Event()
pause_event = threading.Event()

# --- MEDICION ---
def N_stat_msr():
    i_bias = instrument_c.current
    print('curent'+str(i_bias))
    mode = float(dpg.get_value('auto'))
    meas_v = []
    sent_i = []
    for i in np.arange(1, 1+int(dpg.get_value("N_stat"))):
        instrument_c.current = float(i_bias)
        instrument_c.operate = True
        med_v = instrument_v.measure_voltage()
        while float(instrument_v.custom_command('*OPC?')) != 1:
            print('opc?1')
        if mode == 1:
            if np.abs(float(med_v)) > float(dpg.get_value('v_scale_max')):
                if float(i_bias) > 1e-9:
                    i_bias = format(float(i_bias)/10, '.3e')
                pass
            elif np.abs(float(med_v)) < float(dpg.get_value('v_scale_min')):
                if float(i_bias) < 10e-3:
                    i_bias = format(float(i_bias)*10, '.3e')
                pass
        meas_v.append(np.abs(med_v))
        sent_i.append(np.abs(float(i_bias)))
    data_ls = [float(controller.read_temperature()), float(controller.get_setpoint()), float(controller.get_HTR())]
    for i in np.arange(1, 1+int(dpg.get_value("N_stat"))):
        instrument_c.current = -float(i_bias)
        instrument_c.operate = True
        med_v = instrument_v.measure_voltage()
        while float(instrument_v.custom_command('*OPC?')) != 1:
            print('opc?2')
        if mode == 1:
            if np.abs(float(med_v)) > float(dpg.get_value('v_scale_max')):
                if float(i_bias) > 1e-9:
                    i_bias = format(float(i_bias)/10, '.3e')
                pass
            elif np.abs(float(med_v)) < float(dpg.get_value('v_scale_min')):
                if float(i_bias) < 10e-3:
                    i_bias = format(float(i_bias)*10, '.3e')
                pass
        meas_v.append(np.abs(med_v))
        sent_i.append(np.abs(float(i_bias)))
    instrument_c.operate = False
    v_mean = np.mean(meas_v)
    i_mean = np.mean(sent_i)
    return [v_mean, i_mean, data_ls]

def measurement_worker(worker_params):
    """
    Esta función contiene la lógica principal de medición.
    Funciona en un hilo separado para mantener la GUI responsiva.
    Se comunica con la GUI a través de las colas `results_queue` y `command_queue`.
    """
    print("Worker Thread: Iniciado.")
    # Unpack parameters passed from the GUI
    instrument_params = worker_params['instrument_params']
    measurement_table = worker_params['measurement_table']
    file_info = worker_params['file_info']
    
    # State variables for the worker thread, initialized from GUI values
    worker_state = {
        "vlim": instrument_params['vlim'],
        "M_in": instrument_params['M_in'],
        "i_bias": instrument_params['i_bias'],
        "rango_v": instrument_params['rango_v'],
    }

    # Initialize plot data lists
    t_plot, T_plot, Ts_plot, Pot_plot, r1_plot, r2_plot = [], [], [], [], [], []
    tiempo_total = time.time()

    # --- MAIN MEASUREMENT LOOP ---
    for n, row_params in enumerate(measurement_table):
        if stop_event.is_set(): break
        
        # --- RAMP TEMPERATURE ---
        target_setpoint = row_params['setpoint']
        rate = row_params['rate']
        
        results_queue.put({'type': 'dpg_set_value', 'tag': 'tal', 'value': f"Rampa a {target_setpoint} K..."})
        
        current_temp = controller.read_temperature()
        new_setpoint = controller.read_temperature()

        instrument_c.current = worker_state['i_bias']
        instrument_c.voltage = worker_state['vlim']
        instrument_c.operate = False
        instrument_v.set_range(worker_state['rango_v'])

        supply.apply(2.6) # Voltaje inicial del motor
        v = 2.6
        pause_v = 0
        
        tmed = 1
        t0_lectura = time.time()

        window_size = 7 
        t_window = deque(maxlen=window_size)
        T_window = deque(maxlen=window_size)
        dTdt = 0.0 # Initialize the derivative

        while abs(current_temp - target_setpoint) > 0.5:
            if stop_event.is_set(): return
            calc_tmed = time.time()
            # Aca se le pueden pasar comandos desde la GUI
            try:
                cmd = command_queue.get(block=False)
                if cmd['action'] == 'update_vars':
                    worker_state['M_in'] = cmd['voltage']
                    supply.apply(worker_state['M_in'])
                    v = worker_state['M_in']
                    worker_state['i_bias'] = cmd['i_bias']
                    instrument_c.current = worker_state['i_bias']
                    worker_state['vlim'] = cmd['vlim']
                    instrument_c.voltage = worker_state['vlim']
                    worker_state['rango_v'] = cmd['rango_v']
                    instrument_v.set_range(worker_state['rango_v'])
            except queue.Empty:
                pass
            
            # Mover el setpoint en pasos pequeños
            step = rate / 60 * tmed # K per second
            if not pause_event.is_set():
                pause_v = 0
                if target_setpoint > current_temp:
                    new_setpoint = min(new_setpoint + step, target_setpoint)
                else:
                    new_setpoint = max(new_setpoint - step, target_setpoint)
                controller.set_setpoint(new_setpoint)
                current_temp = controller.read_temperature()
                supply.apply(v)
                if float(current_temp)>float(new_setpoint)+1.5 and v > float(dpg.get_value("mlo")) and float(controller.get_HTR())<10.0:
                    v -= 0.1
                elif float(current_temp)<float(new_setpoint)-1.5 and v < float(dpg.get_value("mhi")) and float(controller.get_HTR())>70.0:
                    v += 0.1
                elif float(current_temp)<float(new_setpoint)+1.5 and float(current_temp)>float(new_setpoint)-1.5:
                    v = 2.6
                if v < float(dpg.get_value("mlo")): v = float(dpg.get_value("mlo"))
                if v > float(dpg.get_value("mhi")): v = float(dpg.get_value("mhi"))
            
            if pause_event.is_set():
                if pause_v == 0:
                    pause_v = 1
                    v = 2.6
                    supply.apply(v)

            # --- Lectura durante la rampa ---
            current_time = time.time()
            t_window.append(current_time)
            T_window.append(current_temp)
            v_mean, i_mean, data_ls = N_stat_msr()
            resistance = v_mean / i_mean if i_mean != 0 else float('inf')
            if len(t_window) > 1:
                # np.polyfit(x, y, 1) fits a 1st-degree polynomial (a line) to the data
                # and returns the coefficients [slope, intercept]. We only need the slope.
                # The slope is the derivative in degrees per second.
                slope_per_second = np.polyfit(t_window, T_window, 1)[0]
                
                # Convert from degrees/second to degrees/minute
                dTdt = slope_per_second * 60
            else:
                # Not enough data yet, keep derivative at 0
                dTdt = 0.0

            # Preparar y enviar resultados a la GUI
            t_tot = time.time() - tiempo_total
            t_tar = time.time() - t0_lectura
            row_to_save = [time.strftime("%H:%M:%S", time.localtime()), data_ls[0], data_ls[1], data_ls[2], v_mean, i_mean, resistance, v_mean, i_mean, resistance]
            results_queue.put({'type': 'add_row', 'values': row_to_save})
            # Enviar datos en vivo a la ventana de control
            results_queue.put({'type': 'live_data', 'data': {'T': data_ls[0], 'Ts': data_ls[1], 'Pot': data_ls[2], 'V_motor': supply.measure_voltage(), 'R1': resistance, 'R2': resistance, 'ttotal': time.strftime("%H:%M:%S", time.gmtime(t_tot)), 'ttarea': time.strftime("%H:%M:%S", time.gmtime(t_tar)), 'dTdt': np.round(dTdt, 2)}})
            
            # Enviar datos al plot
            t_plot.append(t_tot)
            T_plot.append(data_ls[0])
            Ts_plot.append(data_ls[1])
            Pot_plot.append(data_ls[2])
            r1_plot.append(resistance)
            r2_plot.append(resistance)
            plot_data = {
                "T_act_p": [t_plot, T_plot], "T_setp_p": [t_plot, Ts_plot], "Pot_p": [t_plot, Pot_plot],
                "r_1_p": [t_plot[:-1], r1_plot[:-1]], "r_2_p": [t_plot[:-1], r2_plot[:-1]],
                "R1_p": [T_plot[:-1], r1_plot[:-1]], "R2_p": [T_plot[:-1], r2_plot[:-1]],
                "r_1_p_latest": [t_plot[-1:], r1_plot[-1:]], "r_2_p_latest": [t_plot[-1:], r2_plot[-1:]],
                "R1_p_latest": [T_plot[-1:], r1_plot[-1:]], "R2_p_latest": [T_plot[-1:], r2_plot[-1:]],
            }
            results_queue.put({'type': 'plot_data', 'data': plot_data})
            tmed = time.time() - calc_tmed
            print('Tiempo medición: '+str(np.round(tmed,2)))

        # --- ESTABILIZACIÓN ---
        t_estabilización = time.time()
        while time.time() - t_estabilización < float(dpg.get_value("T_est")):
            print(time.time() - t_estabilización)
            print(float(dpg.get_value("T_est")))
            if stop_event.is_set(): return
            if row_params['estable'] == 0: break

            calc_tmed = time.time()
            # Aca se le pueden pasar comandos desde la GUI
            try:
                cmd = command_queue.get(block=False)
                if cmd['action'] == 'update_vars':
                    worker_state['M_in'] = cmd['voltage']
                    supply.apply(worker_state['M_in'])
            except queue.Empty:
                pass
            
            if not pause_event.is_set():
                pause_v = 0
                current_temp = controller.read_temperature()
                supply.apply(v)
                if float(current_temp)>float(new_setpoint)+1.5 and v > float(dpg.get_value("mlo")) and float(controller.get_HTR())<10.0:
                    v -= 0.1
                elif float(current_temp)<float(new_setpoint)-1.5 and v < float(dpg.get_value("mhi")) and float(controller.get_HTR())>70.0:
                    v += 0.1
                elif float(current_temp)<float(new_setpoint)+1.5 and float(current_temp)>float(new_setpoint)-1.5:
                    v = 2.6
                if v < float(dpg.get_value("mlo")): v = float(dpg.get_value("mlo"))
                if v > float(dpg.get_value("mhi")): v = float(dpg.get_value("mhi"))
            
            if pause_event.is_set():
                if pause_v == 0:
                    pause_v = 1
                    v = 2.6
                    supply.apply(v)

            # --- Lectura durante la estabilización ---
            v_mean, i_mean, data_ls = N_stat_msr()
            resistance = v_mean / i_mean if i_mean != 0 else float('inf')

            # Preparar y enviar resultados a la GUI
            t_tot = time.time() - tiempo_total
            t_tar = time.time() - t_estabilización
            row_to_save = [time.strftime("%H:%M:%S", time.localtime()), data_ls[0], data_ls[1], data_ls[2], v_mean, i_mean, resistance, v_mean, i_mean, resistance]
            results_queue.put({'type': 'add_row', 'values': row_to_save})
            
            # Enviar datos en vivo a la ventana de control
            results_queue.put({'type': 'live_data', 'data': {'T': data_ls[0], 'Ts': data_ls[1], 'Pot': data_ls[2], 'V_motor': supply.measure_voltage(), 'R1': resistance, 'R2': resistance, 'ttotal': time.strftime("%H:%M:%S", time.gmtime(t_tot)), 'ttarea': time.strftime("%H:%M:%S", time.gmtime(t_tar)), 'dTdt': np.round(dTdt, 2)}})
            
            # Enviar datos al plot
            t_plot.append(t_tot)
            T_plot.append(data_ls[0])
            Ts_plot.append(data_ls[1])
            Pot_plot.append(data_ls[2])
            r1_plot.append(resistance)
            r2_plot.append(resistance)
            plot_data = {
                "T_act_p": [t_plot, T_plot], "T_setp_p": [t_plot, Ts_plot], "Pot_p": [t_plot, Pot_plot],
                "r_1_p": [t_plot[:-1], r1_plot[:-1]], "r_2_p": [t_plot[:-1], r2_plot[:-1]],
                "R1_p": [T_plot[:-1], r1_plot[:-1]], "R2_p": [T_plot[:-1], r2_plot[:-1]],
                "r_1_p_latest": [t_plot[-1:], r1_plot[-1:]], "r_2_p_latest": [t_plot[-1:], r2_plot[-1:]],
                "R1_p_latest": [T_plot[-1:], r1_plot[-1:]], "R2_p_latest": [T_plot[-1:], r2_plot[-1:]],
            }
            results_queue.put({'type': 'plot_data', 'data': plot_data})
            tmed = time.time() - calc_tmed
            print('Tiempo medición: '+str(np.round(tmed,2)))
            results_queue.put({'type': 'dpg_set_value', 'tag': 'tal', 'value': f"Estabilizando a {target_setpoint} K..."})
        
        # --- TAKE FINAL MEASUREMENTS AT STABLE TEMP ---
        # if row_params['estable'] > 0:
        #     results_queue.put({'type': 'dpg_set_value', 'tag': 'tal', 'value': f"Midiendo a {target_setpoint} K..."})

    results_queue.put({'type': 'dpg_set_value', 'tag': 'tal', 'value': "Terminado"})
    results_queue.put({'type': 'measurement_finished'})
    print("Worker Thread: Finished.")

# --- DPG CALLBACKS (run in the main GUI thread) ---

def resize_layout_callback(sender, app_data):
    """
    This callback fires once on startup and whenever the viewport is resized.
    It recalculates and sets the widths of the three subwindows.
    """
    if not dpg.does_item_exist("Archivo"):
        print('GUI: Main windows not yet created, skipping resize.')
        return
    print('GUI: Resizing layout based on viewport size.')
    # Get the width of the viewport's drawable area (client width)
    v_w = dpg.get_viewport_client_width() 

    # Calculate the width for each window.
    # We use integer division for the first two.
    win_ctrl = v_w // 3.5
    
    # The last window gets the remaining space to handle
    # any rounding (e.g., if width is 1000, 333 + 333 + 334).
    win_long = v_w - (win_ctrl * 2)
    win_short = win_long // 2

    v_h = dpg.get_viewport_client_height() 
    
    if v_h >= 670:
        h_arch = 100
        h_fuente = 220
        h_temp = 130
        h_live = 220
        h_tabla = 670
        h_plot = 335
    else:
        h_arch = 100
        h_fuente = v_h * 0.35
        h_temp = v_h * 0.2
        h_live = v_h * 0.35
        h_tabla = v_h
        h_plot = v_h * 0.5

    # Apply the calculated widths to the subwindows
    dpg.configure_item("Archivo", 
                       pos=[0, 0], 
                       width=win_ctrl, 
                       height=h_arch)
    dpg.configure_item("Fuente & Nanovoltímetro", 
                       pos=[0, h_arch+18], 
                       width=win_ctrl, 
                       height=h_fuente)
    dpg.configure_item("Control Temperatura", 
                       pos=[0, h_arch + h_fuente + 18], 
                       width=win_ctrl, 
                       height=h_temp)
    dpg.configure_item("Medición T", 
                       pos=[win_ctrl, 0], 
                       width=win_ctrl, 
                       height=h_tabla)
    dpg.configure_item("Temperatura", 
                       pos=[win_ctrl * 2, 0], 
                       width=win_long, 
                       height=h_plot)
    dpg.configure_item("R(t)", 
                       pos=[win_ctrl * 2, h_plot + 18], 
                       width=win_short, 
                       height=h_plot)
    dpg.configure_item("R(T)", 
                       pos=[win_ctrl * 2 + win_short, h_plot + 18], 
                       width=win_short, 
                       height=h_plot)
    if dpg.does_item_exist("live_control_window"):
        dpg.configure_item("live_control_window", 
                           pos=[0, h_arch+h_fuente+h_temp + 18], 
                           width=win_ctrl, 
                           height=h_live)

def start_measurement_callback():
    """ Gathers all parameters from the GUI and starts the worker thread. """
    # 1. Gather all parameters from GUI widgets
    instrument_params = {
        'vlim': float(dpg.get_value("vlim")),
        'M_in': float(dpg.get_value("M_in")),
        'i_bias': float(dpg.get_value("i_bias")),
        'rango_v': float(dpg.get_value("rango_v")),
    }
    
    file_info = {
        'directory': dpg.get_value("selected_file_text"),
        'file_name': dpg.get_value("Muestra")
    }

    measurement_table = []
    table_rows = dpg.get_item_children("Tabla", 1)
    for row in table_rows:
        cells = dpg.get_item_children(row, 1)
        measurement_table.append({
            'setpoint': float(dpg.get_value(cells[0])),
            'rate': float(dpg.get_value(cells[1])),
            'estable': float(dpg.get_value(cells[2])),
        })
        
    worker_params = {
        'instrument_params': instrument_params,
        'measurement_table': measurement_table,
        'file_info': file_info,
    }

    # 2. Reset state and start the thread
    stop_event.clear()
    # Clear old data from queues
    while not results_queue.empty(): results_queue.get()
    while not command_queue.empty(): command_queue.get()

    # Create the live control window
    create_live_control_window()
    add_row(['Tiempo', 'T(K)', 'Setpoint(K)', 'Heater','V muestra 1 (V)', 'I muestra 1 (A)', 'R muestra 1 (Ohm)', 'V muestra 2 (V)', 'I muestra 2 (A)', 'R muestra 2 (Ohm)'])

    worker_thread = threading.Thread(target=measurement_worker, args=(worker_params,), daemon=True)
    worker_thread.start()

    # 3. Update GUI to reflect running state
    dpg.configure_item("comenzar_button", enabled=False)
    dpg.configure_item("stop_button", enabled=True)
    dpg.configure_item("pause_button", enabled=True)

def stop_measurement_callback():
    """ Signals the worker thread to stop. """
    print("GUI: Stop button clicked. Signaling thread.")
    stop_event.set()
    dpg.configure_item("comenzar_button", enabled=True)
    dpg.configure_item("stop_button", enabled=False)

def pause_measurement_callback():
    """ Signals the worker thread to pause. """
    print("GUI: Pause button clicked. Signaling thread.")
    if pause_event.is_set():
        pause_event.clear()
        dpg.configure_item("comenzar_button", enabled=False)
        dpg.configure_item("stop_button", enabled=True)
        dpg.configure_item("pause_button", enabled=True)
    else:
        pause_event.set()
    dpg.configure_item("comenzar_button", enabled=False)
    dpg.configure_item("stop_button", enabled=True)
    dpg.configure_item("pause_button", enabled=True)

def update_vars_callback():
    """ Puts an 'update vars' command into the command queue for the worker. """
    voltage = float(dpg.get_value("M_in"))
    i_bias = float(dpg.get_value("i_bias"))
    vlim = float(dpg.get_value("vlim"))
    rango_v = float(dpg.get_value("rango_v"))
    command_queue.put({'action': 'update_vars', 'voltage': voltage, 'i_bias': i_bias, 'vlim': vlim, 'rango_v': rango_v})
    print(f"GUI: Actualizando por 'update_vars'.")
    # For immediate feedback, also update mock supply from GUI thread
    supply.apply(voltage) 
    saved = np.loadtxt('config.txt', delimiter=',')
    np.savetxt('config.txt', [f'{0},{0},{0},{0},{dpg.get_value("M_in")},{saved[5]}'], fmt='%s')

# --- GUI HELPER FUNCTIONS ---

def add_row(values):
    directory = dpg.get_value("selected_file_text")
    file_name = dpg.get_value("Muestra")
    file_path = os.path.join(directory, file_name + '.csv')
    try:
        with open(file_path, mode='a', newline='') as file:
            csv.writer(file).writerow(values)
    except Exception as e:
        print(f"Error writing to file: {e}")

def crea_tablas_T():
    T0, TF, sep, rate, est = map(float, [dpg.get_value(t) for t in ["T0", "TF", "sep", "rate", "est"]])
    N = int(np.abs(T0 - TF) / sep) + 1
    tes = np.round(np.linspace(T0, TF, N), 1)
    for t in tes:
        with dpg.table_row(parent="Tabla"):
            dpg.add_input_text(default_value=f"{t}")
            dpg.add_input_text(default_value=f"{rate}")
            dpg.add_input_text(default_value=f"{est}")

def reset_table_T():
    dpg.delete_item("Tabla", children_only=False)
    with dpg.table(header_row=True, tag="Tabla", borders_innerH=True, borders_outerH=True,
                    borders_innerV=True, borders_outerV=True, height=-30, 
                    no_host_extendY=True, scrollY=True, parent="g_col"):
        dpg.add_table_column(label="T (K)")
        dpg.add_table_column(label="Rate (K/min)")
        dpg.add_table_column(label="Estable?")
    
def file_selected_callback(sender, app_data):
    dpg.set_value("selected_file_text", app_data['file_path_name'])

def default_file_selected_callback():
    dpg.add_file_dialog(directory_selector=True, show=True, callback=set_default_directory, tag="default_file_dialog", width=700 ,height=200)

def set_default_directory(sender, app_data):
    np.savetxt(f'{os.getcwd()}\\config.txt', [f'{0},{0},{0},{0},{dpg.get_value("M_in")},{app_data['file_path_name']}'], fmt='%s')
    print(f"GUI: Default directory set to {app_data['file_path_name']}")
    print(f'{os.getcwd()}\\config.txt')

def create_live_control_window():
    if dpg.does_item_exist("live_control_window"):
        return
    viewport_width = dpg.get_viewport_client_width()
    win_ctrl = viewport_width // 3.5

    v_h = dpg.get_viewport_client_height() 
    
    if v_h >= 670:
        h_arch = 100
        h_fuente = 220
        h_temp = 130
        h_live = 220
        h_tabla = 670
        h_plot = 335
    else:
        h_arch = 100
        h_fuente = v_h * 0.35
        h_temp = v_h * 0.2
        h_live = v_h * 0.35
        h_tabla = v_h
        h_plot = v_h * 0.5


    
    with dpg.window(label="Control en vivo", width=win_ctrl, height=h_live, pos=(0,h_arch+h_fuente+h_temp+18), 
                    tag="live_control_window", 
                    on_close=lambda: dpg.delete_item("live_control_window")):
        
        with dpg.table(header_row=False, resizable=True, policy=dpg.mvTable_SizingStretchSame, 
                       height=-1): 
            dpg.add_table_column()
            dpg.add_table_column()
            dpg.add_table_column()

            with dpg.table_row():
                with dpg.group():
                    dpg.add_text("T actual (K)")
                    dpg.add_text("0.00 K", tag="tl")
                with dpg.group():
                    dpg.add_text("T setpoint (K)")
                    dpg.add_text("0.00 K", tag="sl")
                with dpg.group():
                    dpg.add_text("Potencia (%)")
                    dpg.add_text("0.00 %", tag="pl")
            
            with dpg.table_row():
                with dpg.group():
                    dpg.add_text("Volt. motor (V)")
                    dpg.add_text("2.6 V", tag="vl")
                with dpg.group():
                    dpg.add_text("dT/dt")
                    dpg.add_text("0 K/min", tag="dTdt")

            with dpg.table_row():
                with dpg.group():
                    dpg.add_text("R muestra 1")
                    dpg.add_text("0.00e+0 Ohm", tag="r1l")
                with dpg.group():
                    dpg.add_text("R muestra 2")
                    dpg.add_text("0.00e+0 Ohm", tag="r2l")
            
            with dpg.table_row():
                with dpg.group():
                    dpg.add_text("Tiempo total")
                    dpg.add_text("00:00:00", tag="ttot")
                with dpg.group():
                    dpg.add_text("Tiempo tarea")
                    dpg.add_text("00:00:00", tag="ttar")
                with dpg.group():
                    dpg.add_text("Tarea actual")
                    dpg.add_text("Idle", tag="tal")

def create_help_window():
    if dpg.does_item_exist("Ayuda"):
        return
    viewport_width = dpg.get_viewport_client_width()
    width_ayu = viewport_width // 4
    v_h = dpg.get_viewport_client_height() 
    height_ayu = v_h // 2
    with dpg.window(label="Ayuda", width=width_ayu, height=height_ayu, pos=(viewport_width // 3,v_h // 4), 
                    tag="Ayuda", 
                    on_close=lambda: dpg.delete_item("Ayuda")):
        dpg.add_text("Ayuda")

# --- INITIALIZATION AND GUI LAYOUT ---
dpg.create_context()
dpg.create_viewport(title='Medición', width=1280, height=720)
w=370 # window width

# Initialize instruments
controller = lsdrc91ca.LakeShoreDRC91CA()
supply = agie3643a.AgilentE3643A()
instrument_v = a34420a.Agilent34420A()
instrument_c = k224.KEITHLEY_224()

# File Dialog
dpg.add_file_dialog(directory_selector=True, show=False, callback=file_selected_callback, tag="file_dialog")
with dpg.window(label="Archivo", tag="Archivo"):
    dpg.add_button(label="Choose Directory", callback=lambda: dpg.show_item("file_dialog"), width=-1)
    dpg.add_input_text(default_value=os.getcwd(), tag="selected_file_text", width=-1, readonly=True)
    dpg.add_input_text(label=f"-{time.strftime(' @ %Y-%m-%d %H:%M:%S')}", tag="Muestra", 
                       default_value=f"Muestra", 
                       width=-200)

# Control Instrumental
with dpg.window(label="Fuente & Nanovoltímetro", tag="Fuente & Nanovoltímetro"):
    with dpg.table(header_row=False, resizable=True, policy=dpg.mvTable_SizingStretchSame):
        dpg.add_table_column()
        dpg.add_table_column()
        dpg.add_table_column()

        with dpg.table_row():
            dpg.add_text("V-Lim k224")
            dpg.add_text("I k224")
            dpg.add_text("Autorange (1/0)")

        with dpg.table_row():
            dpg.add_input_text(label="V", default_value=f"{1}", tag="vlim", width=-20)
            dpg.add_input_text(label="A", default_value=f"{0.001}", tag="i_bias", width=-20)
            dpg.add_input_text(default_value=f"{0}", tag="auto", width=-20)

        with dpg.table_row():
            dpg.add_text("Max. V 34420")
            dpg.add_text("Mín. V 34420")
            dpg.add_text("Rango V 34420")

        with dpg.table_row():
            dpg.add_input_text(label="V", default_value=f"{0.01}", tag="v_scale_max", width=-20)
            dpg.add_input_text(label="V", default_value=f"{0.001}", tag="v_scale_min", width=-20)
            dpg.add_input_text(default_value=f"{0.1}", width=-20, tag="rango_v")

        with dpg.table_row():
            dpg.add_text("N biases")
            dpg.add_text("N mediciones")

        with dpg.table_row():
            dpg.add_input_text(default_value=f"{3}", tag="N_stat", width=-20)
            dpg.add_input_text(default_value=f"{3}", tag="ctd_msr", width=-20)

        with dpg.table_row():
            dpg.add_text("")
            dpg.add_text("")
            dpg.add_text("")

        with dpg.table_row():
            dpg.add_text("")
            dpg.add_button(label="Update", callback=update_vars_callback, width=-20)

# Control Temperatura
with dpg.window(label="Control Temperatura", tag="Control Temperatura"):
    with dpg.table(header_row=False, resizable=True, policy=dpg.mvTable_SizingStretchSame):
        dpg.add_table_column()
        dpg.add_table_column()
        dpg.add_table_column()

        with dpg.table_row():
            dpg.add_text("Estabilidad (s)")
            dpg.add_text("Voltaje motor")
            dpg.add_text("Motor Máx")

        with dpg.table_row():
            dpg.add_input_text(default_value=f"60", tag="T_est", width=-1)
            dpg.add_input_text(default_value=f"{2.6}", tag="M_in", width=-1)
            dpg.add_input_text(default_value=f"{4.8}", tag="mhi", width=-1)

        with dpg.table_row():
            dpg.add_text("")
            dpg.add_text("")
            dpg.add_text("Motor Mín")

        with dpg.table_row():
            dpg.add_text("")
            dpg.add_text("")
            dpg.add_input_text(default_value=f"{1.2}", tag="mlo", width=-1)

# Tabla de Temperaturas
with dpg.window(label="Medición T", tag="Medición T"):
    with dpg.table(header_row=False, resizable=True, policy=dpg.mvTable_SizingStretchSame):
        dpg.add_table_column()
        dpg.add_table_column()
        dpg.add_table_column()

        with dpg.table_row():
            dpg.add_text("T inicial (K)")
            dpg.add_text("T final (K)")
            dpg.add_text("dT (K)")

        with dpg.table_row():
            dpg.add_input_text(default_value=f"{295}", tag="T0", width=-1)
            dpg.add_input_text(default_value=f"{295}", tag="TF", width=-1)
            dpg.add_input_text(default_value=f"{20}", tag="sep", width=-1)

        with dpg.table_row():
            dpg.add_text("Rate (K/min)")
            dpg.add_text("Estable? (1/0)")
            dpg.add_text("") # Empty cell

        with dpg.table_row():
            dpg.add_input_text(default_value=f"{2}", tag="rate", width=-1)
            dpg.add_input_text(default_value=f"{1}", tag="est", width=-1)
            dpg.add_button(label="Agregar", callback=crea_tablas_T, width=-1)

    with dpg.group(tag="g_col"):
        with dpg.table(header_row=True, tag="Tabla", borders_innerH=True, borders_outerH=True,
                       borders_innerV=True, borders_outerV=True, height=-30, 
                       no_host_extendY=True, scrollY=True):
            dpg.add_table_column(label="T (K)")
            dpg.add_table_column(label="Rate (K/min)")
            dpg.add_table_column(label="Estable?")
    
    with dpg.group(horizontal=True):
        dpg.add_button(label="Limpiar", callback=reset_table_T, width=70)
        dpg.add_button(label="Comenzar", callback=start_measurement_callback, tag="comenzar_button", width=70)
        dpg.add_button(label="Detener", callback=stop_measurement_callback, tag="stop_button", enabled=False, width=70)
        dpg.add_button(label="Pausa", callback=pause_measurement_callback, tag="pause_button", enabled=True, width=70)

# Plots
with dpg.theme(tag="latest_point_theme"):
    with dpg.theme_component(dpg.mvScatterSeries):
        dpg.add_theme_color(dpg.mvPlotCol_Line, (132, 222, 215, 255), category=dpg.mvThemeCat_Plots)
        dpg.add_theme_color(dpg.mvPlotCol_Fill, (132, 222, 215, 255), category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Square, category=dpg.mvThemeCat_Plots)
        dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 5, category=dpg.mvThemeCat_Plots)

with dpg.window(label='Temperatura', tag="Temperatura", pos=(w+370,0)):
    with dpg.plot(height=-1, width=-1):
            dpg.add_plot_axis(dpg.mvXAxis, label="Tiempo (s)", tag="t_temp_ax", auto_fit=True)
            dpg.add_plot_axis(dpg.mvYAxis, label="Temperatura (K)", tag="T_setp_y", auto_fit=True)
            dpg.add_scatter_series([], [], label="T Setpoint", parent="T_setp_y", tag="T_setp_p")
            dpg.add_scatter_series([], [], label="T Actual", parent="T_setp_y", tag="T_act_p")
            dpg.add_plot_axis(dpg.mvYAxis, label="Potencia (%)", tag="Pot_y")
            dpg.set_axis_limits("Pot_y", -1, 101)
            dpg.add_scatter_series([], [], label="Potencia", parent="Pot_y", tag="Pot_p")
            dpg.add_plot_legend()

with dpg.window(label='R(t)', tag="R(t)", pos=(w+370,285)):
    with dpg.plot(height=-1, width=-1):
            dpg.add_plot_axis(dpg.mvXAxis, label="Tiempo (s)", tag="t_temp_ax_m", auto_fit=True)
            dpg.add_plot_axis(dpg.mvYAxis, label="Resistencia (Ohm)", tag="Res_y", auto_fit=True)
            # Series for all historical data
            dpg.add_scatter_series([], [], label="Muestra 1", parent="t_temp_ax_m", tag="r_1_p")
            dpg.add_scatter_series([], [], label="Muestra 2", parent="t_temp_ax_m", tag="r_2_p")
            # Series specifically for the single latest point (no label)
            dpg.add_scatter_series([], [], parent="t_temp_ax_m", tag="r_1_p_latest")
            dpg.add_scatter_series([], [], parent="t_temp_ax_m", tag="r_2_p_latest")
            dpg.bind_item_theme("r_1_p_latest", "latest_point_theme")
            dpg.bind_item_theme("r_2_p_latest", "latest_point_theme")

with dpg.window(label='R(T)', tag="R(T)", pos=(w+370+275,285)):
    with dpg.plot(height=-1, width=-1):
            dpg.add_plot_axis(dpg.mvXAxis, label="Temperatura (K)", tag="t_temp_ax_r", auto_fit=True)
            dpg.add_plot_axis(dpg.mvYAxis, label="Resistencia (Ohm)", tag="rdt_y", auto_fit=True)
            # Series for all historical data
            dpg.add_scatter_series([], [], label="Resistencia 1", parent="t_temp_ax_r", tag="R1_p")
            dpg.add_scatter_series([], [], label="Resistencia 2", parent="t_temp_ax_r", tag="R2_p")
            # Series specifically for the single latest point (no label)
            dpg.add_scatter_series([], [], parent="t_temp_ax_r", tag="R1_p_latest")
            dpg.add_scatter_series([], [], parent="t_temp_ax_r", tag="R2_p_latest")
            dpg.bind_item_theme("R1_p_latest", "latest_point_theme")
            dpg.bind_item_theme("R2_p_latest", "latest_point_theme")

# --- START GUI ---
dpg.setup_dearpygui()
dpg.maximize_viewport()

# Cargar configuración guardada
if os.path.exists('config.txt'):
    saved = np.loadtxt('config.txt', delimiter=',', dtype='str')
    dpg.set_value("selected_file_text", saved[5])
    dpg.set_value("M_in", saved[4])
else:
    np.savetxt('config.txt', [f'{0},{0},{0},{0},{dpg.get_value("M_in")},{os.getcwd()}'], fmt='%s')

with dpg.viewport_menu_bar():
    with dpg.menu(label="Opciones"):
        dpg.add_menu_item(label="Directorio default", callback=default_file_selected_callback)
        dpg.add_menu_item(label="Setting 2")

    dpg.add_menu_item(label="Ayuda", callback=create_help_window)

dpg.show_viewport()
# --- MAIN RENDER LOOP ---
while dpg.is_dearpygui_running():
    # This is the core of the solution. The main GUI loop is always running
    # and can process results from the worker thread without blocking.
    dpg.set_viewport_resize_callback(resize_layout_callback)
    try:
        # Check the results queue for data from the worker thread
        msg = results_queue.get(block=False)

        if msg['type'] == 'dpg_set_value': #Si la señal actualiza un valor de dpg, lo hace
            if dpg.does_item_exist(msg['tag']):
                dpg.set_value(msg['tag'], msg['value'])

        elif msg['type'] == 'live_data': #Si la señal es de datos en vivo, actualiza los valores correspondientes
            data = msg['data']
            dpg.set_value('tl', f"{data['T']:.2f} K")
            dpg.set_value('sl', f"{data['Ts']:.2f} K")
            dpg.set_value('pl', f"{data['Pot']:.1f} %")
            dpg.set_value('vl', f"{data['V_motor']:.3f} V")
            dpg.set_value('r1l', f"{data['R1']:.3e} Ohm")
            dpg.set_value('r2l', f"{data['R2']:.3e} Ohm")
            dpg.set_value('ttot', f"{data['ttotal']}")
            dpg.set_value('ttar', f"{data['ttarea']}")
            dpg.set_value('dTdt', f"{data['dTdt']} K/min")

        elif msg['type'] == 'plot_data': #Si la señal es de datos para graficar, actualiza los gráficos
            for tag, data in msg['data'].items():
                if dpg.does_item_exist(tag):
                    dpg.set_value(tag, data)
        
        elif msg['type'] == 'add_row': #Si la señal es para agregar una fila a la tabla, lo hace
            add_row(msg['values'])

        elif msg['type'] == 'measurement_finished': #Si la señal indica stop, lo detiene
            dpg.configure_item("comenzar_button", enabled=True)
            dpg.configure_item("stop_button", enabled=False)

    except queue.Empty:
        # Resultado vacío, no hay nada que procesar
        pass

    dpg.render_dearpygui_frame()

dpg.destroy_context()