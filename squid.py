#%%
import matplotlib.pyplot as plt
import numpy as np

data = np.genfromtxt('e:/trabajo/tesis 3/tesisfisica/squid/SIO1/MdeT_1000G_FC.rso.dat', skip_header=32, delimiter=',', unpack=True)
# Create the plot
plt.figure(figsize=(4, 3), dpi=450)
plt.plot(data[3][:-100], data[4][:-100], c="#47C0B0", lw=2)

plt.xlabel('T (K)')
plt.ylabel('M (emu)')

# Show the plot
# plt.vlines(100,0,0.000178, linestyles='--', label='$T_M=100 $ K', color='k')
# plt.vlines(240,-0.000043,0, linestyles='-.', label='$T_N=240 $ K', color='k')
# plt.ylim(-0.00005, 0.00020)
plt.legend(fontsize='large', frameon=False)
# plt.grid()
plt.show()

#%%
import matplotlib.pyplot as plt
import numpy as np
%matplotlib inline
data = np.genfromtxt('e:/porno/tesis 3/tesisfisica/datos1VNOV.csv', skip_header=0, delimiter=',', unpack=True)


fig, ax1 = plt.subplots()
ax2 = ax1.twinx()

lns1=ax1.plot(data[0], data[1], marker='o', lw=4, c='#4A85F1',label ='$R_{inst}$')
lns2=ax2.plot(data[0], data[2], marker='*', lw=4, color="#F1B74A", label='$\gamma$')
ax1.grid()
ax1.set_xlabel('Temperatura (K)')
ax1.set_ylabel('R ($\Omega$)')
ax2.set_ylabel('$\gamma$')
lns = lns1+lns2
labs = [l.get_label() for l in lns]
ax1.legend(lns, labs, loc=0)
# ax2.grid(True)
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
