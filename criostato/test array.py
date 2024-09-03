import dearpygui.dearpygui as dpg

dpg.create_context()

def button_callback(sender, app_data):
    print(f"sender is: {sender}")
    print(f"app_data is: {app_data}")

with dpg.window(label="Tutorial"):
    dpg.add_button(label="Print to Terminal", callback=button_callback, app_data=1)

dpg.create_viewport(title='Custom Title', width=800, height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()