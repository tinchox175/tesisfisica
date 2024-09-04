# -*- coding: utf-8 -*-
"""
Created on Wed Aug 28 15:19:55 2024

@author: Administrator
"""

import dearpygui.dearpygui as dpg

dpg.create_context()

with dpg.window(label="Tutorial"):

    with dpg.table(header_row=True, tag="tabla"):

        # use add_table_column to add columns to the table,
        # table columns use slot 0
        dpg.add_table_column(label="Header 1")
        dpg.add_table_column(label="Header 2")
        dpg.add_table_column(label="Header 3")

        # add_table_next_column will jump to the next row
        # once it reaches the end of the columns
        # table next column use slot 1
        for i in range(0, 4):
            with dpg.table_row():
                for j in range(0, 3):
                    dpg.add_text(f"Row{i} Column{j}")
    def lector(sender, app_data, user_data):
        table_id = "tabla"  # The table id is passed as user_data
        rows = dpg.get_item_children(table_id, 1)  # Slot 1 for regular items (children)

        for row in rows:
            cells = dpg.get_item_children(row, 1)  # Each row's children are cells
            for cell in cells:
                # Access the value of the cell, assuming they are text items
                cell_value = dpg.get_value(cell)
                print(f"Cell value: {cell_value}")
                
    dpg.add_button(label="test", callback=lector)
dpg.create_viewport(title='Custom Title', width=300, height=300)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
