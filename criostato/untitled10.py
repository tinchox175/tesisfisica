# -*- coding: utf-8 -*-
"""
Created on Wed Aug 28 15:19:55 2024

@author: Administrator
"""
import csv

def flier(file_name, values):
    with open(file_name, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(values)

flier('test.csv', [[4,5,6],2,3])