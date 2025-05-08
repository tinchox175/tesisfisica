#%%
import matplotlib.pyplot as plt
import numpy as np

data = np.genfromtxt('e:/porno/tesis 3/tesisfisica/squid/SIO1/MdeT1000G.csv', skip_header=1, delimiter=',', unpack=True)
# Create the plot
plt.figure()
plt.plot(data[3], data[4])

plt.xlabel('Temperatura (K)')
plt.ylabel('Magnetización (emu)')

# Show the plot
plt.vlines(100,0,0.000178, linestyles='--', label='$T_M=100 $ K', color='k')
plt.vlines(240,-0.000043,0, linestyles='-.', label='$T_N=240 $ K', color='k')
plt.ylim(-0.00005, 0.00020)
plt.legend()
plt.grid()
plt.show()

#%%
import matplotlib.pyplot as plt
import numpy as np
%matplotlib inline
data = np.genfromtxt('e:/porno/tesis 3/tesisfisica/datos0.05VNOV.csv', skip_header=0, delimiter=',', unpack=True)


fig, ax1 = plt.subplots()
ax2 = ax1.twinx()

lns1=ax1.plot(data[0], data[1], marker='o', label ='$R_{inst}$')
lns2=ax2.plot(data[0], data[2], marker='*', color='orange', label='$\gamma$')
plt.grid()
ax1.set_xlabel('Temperatura (K)')
ax1.set_ylabel('R (Ohm)')
ax2.set_ylabel('$\gamma$')
lns = lns1+lns2
labs = [l.get_label() for l in lns]
ax1.legend(lns, labs, loc=0)

# plt.show()
# %%
A = 3
B = 5
for i in np.arange(0,50):
    Am = A
    Bm = B
    A = Am+Bm
    B = Am-Bm
print(A)
print(B)
# %%
