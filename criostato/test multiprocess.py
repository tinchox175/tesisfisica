import dearpygui.dearpygui as dpg
dpg.create_context()

dpg.create_viewport(title='Loop Control Example', width=600, height=300)

running = False
loop_var = 0

# This is the function called in intervals to continue the loop
def loop_callback(sender, app_data, user_data):
    global loop_var, running
    if running:
        print(f"Current loop_var value: {loop_var}")
        
        # Example of doing something in a loop
        loop_var += 1
        
        # Check if we should continue the loop
        if loop_var < 10:
            dpg.set_frame_callback(1, loop_callback)
        else:
            running = False

# Button to start the loop
def start_loop_callback(sender, app_data):
    global running, loop_var
    running = True
    loop_var = 0
    dpg.set_frame_callback(1, loop_callback)

# Button to modify the variable during the loop
def modify_variable_callback(sender, app_data):
    global loop_var
    loop_var += 5  # Modify the loop variable from another callback
    print(f"Variable modified: {loop_var}")

# Create the interface
with dpg.window(label="Loop Example"):
    dpg.add_button(label="Start Loop", callback=start_loop_callback)
    dpg.add_button(label="Modify Variable", callback=modify_variable_callback)
    dpg.add_text("Loop variable will be printed to console.")
    
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()