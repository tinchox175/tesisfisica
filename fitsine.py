import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# Define the sine function
def sine_function(x, A, omega, phi, C):
    return A * np.sin(omega * x + phi) + C
m = 0
#off = [0,50,100,150,200]
f = [100,1000,200000]
for n in [27,32,37]:
    data = np.genfromtxt(f'./IVs/2611/B/tek00{n}ALL.csv', unpack=True, delimiter=',', skip_header=20)
    x_data = data[0][500:-1000]
    y_data = data[3][500:-1000]
    ing = [0.2, f[m]*(2*np.pi), 0, 0.200]
    params, params_covariance = curve_fit(sine_function, x_data, y_data, p0=ing)
    A, omega, phi, C = params
    print(f"Fitted parameters: Amplitude={A}, Frequency={omega}, Phase={phi}, Offset={C}")
    fig, (ax1, ax2) = plt.subplots(2,1, sharex=True)
    ax1.plot(x_data, y_data, label='Data')
    f1 = sine_function(x_data, A, omega, phi, C)
    d1 = y_data
    ax1.plot(x_data, sine_function(x_data, A, omega, phi, C), color='red', label='Fit CH3')
    y_data = data[4][500:-1000]
    ing = [0.2, f[m]*(2*np.pi), 0, 0.15]
    params, params_covariance = curve_fit(sine_function, x_data, y_data, p0=ing)
    A, omega, phi, C = params
    print(f"Fitted parameters: Amplitude={A}, Frequency={omega}, Phase={phi}, Offset={C}")
    plt.suptitle(f'TEK{n} f = {omega} Off={200}')
    ax1.plot(x_data, y_data, label='Data')
    ax1.plot(x_data, sine_function(x_data, A, omega, phi, C), color='black', label='Fit CH4')
    ax2.plot(x_data, f1-sine_function(x_data, A, omega, phi, C), zorder=10, c='red')
    ax2.plot(x_data, d1-y_data, c='black')
    plt.legend()
    m+=1
plt.show()
