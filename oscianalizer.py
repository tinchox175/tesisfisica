#%%
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
%matplotlib qt
# Generate example data

for n in np.arange(32,38):
    data = np.genfromtxt(f'./IVs/2611/B/tek00{n}ALL.csv', unpack=True, delimiter=',', skip_header=20)
    x = data[0]
    y = data[1]
    ma = np.mean(y)*1.5
    peaks, properties = find_peaks(y, height=ma, distance=1)
    print(peaks)
    real_peaks = []
    avg_peak_list = []
    for i in np.arange(2,len(peaks[:-1])+1):
        print(peaks[i], peaks[-1])
        if np.abs(peaks[i]-peaks[i-1]) < 5000 and int(peaks[i]) != int(peaks[-1]):
            print('g')
            avg_peak_list.append(peaks[i])
        elif int(peaks[i]) == int(peaks[-1]):
            real_peaks.append(int(np.floor(np.median(avg_peak_list))))
        else:
            print(peaks[i])
            real_peaks.append(int(np.floor(np.median(avg_peak_list))))
            avg_peak_list = []
        # break
    peaks = real_peaks
    peak_mean = []
    plt.figure(figsize=(10, 6))
    for j in peaks:
        new_peaks = []
        for k in np.arange(1,10):
            new_peaks.append(y[j-k])
            new_peaks.append(y[j])
            new_peaks.append(y[j+k])
        peak_mean.append(np.mean(new_peaks))
    m = 0
    colord = ['blue','red','orange','purple','yellow','black','pink']
    for i in peak_mean:
        plt.hlines(i,x[0],x[-1], color=colord[m], label=f'{m}')
        m+=1
    plt.plot(x, y, label="Signal")
    plt.plot(x[peaks], y[peaks], "x", label="Peaks", color="red")
    plt.suptitle(f'{n}')
    plt.title("Peak Detection")
    plt.xlabel("X")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.show()

    print("Peak indices:", peaks)
    #print("Peak heights:", properties["peak_heights"])