import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
%matplotlib qt
# Generate example data
for n in ['04','05','06','07','08']:
    data = np.genfromtxt(f'C:/tesis git/tesisfisica/IVs/2611/B/tek00{n}ALL.csv', unpack=True, delimiter=',', skip_header=20)
    x = data[0]
    y = data[1]
    # Find peaks
    ma = np.mean(y)*1.5
    peaks, properties = find_peaks(y, height=ma, distance=50)
    real_peaks = []
    avg_peak_list = []
    for i in np.arange(2,len(peaks[:-1])+1):
        print(peaks[i], peaks[-1])
        if np.abs(peaks[i]-peaks[i-1]) < 5000 and int(peaks[i]) != int(peaks[-1]):
            avg_peak_list.append(peaks[i])
        elif int(peaks[i]) == int(peaks[-1]):
            real_peaks.append(int(np.floor(np.median(avg_peak_list))))
        else:
            print(peaks[i])
            real_peaks.append(int(np.floor(np.median(avg_peak_list))))
            avg_peak_list = []
        # break
    peaks = real_peaks
    new_peaks = []
    peak_mean = []
    for j in peaks:
        for k in [1,2,3,4,5,6,7,8]:
            new_peaks.append(y[j-k])
            new_peaks.append(y[j])
            new_peaks.append(y[j+k])
        peak_mean.append(np.mean[new_peaks])
    plt.figure(figsize=(10, 6))
    plt.plot(x, y, label="Signal")
    plt.plot(x[peaks], y[peaks], "x", label="Peaks", color="red")
    plt.title("Peak Detection")
    plt.xlabel("X")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.show()

    # Print peak information
    print("Peak indices:", peaks)
    #print("Peak heights:", properties["peak_heights"])