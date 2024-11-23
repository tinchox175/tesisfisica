import dearpygui.dearpygui as dpg
import time
dpg.create_context()

with dpg.window(label="Tutorial"):
    with dpg.table(header_row=False, tag='Tabla'):

        # use add_table_column to add columns to the table,
        # table columns use child slot 0
        dpg.add_table_column()
        dpg.add_table_column()
        dpg.add_table_column()

        # add_table_next_column will jump to the next row
        # once it reaches the end of the columns
        # table next column use slot 1
        for i in range(0, 1):
            with dpg.table_row():
                for j in range(0, 2):
                    dpg.add_text(f"Row{i} Column{j}")
table_id = "Tabla"  
rows = dpg.get_item_children(table_id, 1)
for row in rows:
        cells = dpg.get_item_children(row, 1)
        print(dpg.get_value(cells[0]))
dpg.create_viewport(title='Custom Title', width=800, height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()