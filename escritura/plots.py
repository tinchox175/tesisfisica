import numpy as np
import matplotlib.pyplot as plt

plt.figure(figsize=(4, 3), dpi=400)
x1 = np.linspace(-8, 5, 100)
x2 = np.linspace(-8, 8, 100)
y1 = 1.5 * x1
y2 = 1/5 * x2

# Main solid lines
plt.plot(x1, y1, lw=4, c='#4A85F1')
plt.plot(x2, y2, lw=4, c='#F1B74A')

# Dashed extensions
x1_ext = np.linspace(-9.5, 9.5, 200)
x2_ext = np.linspace(-9.5, 9.5, 200)
y1_ext = 1.5 * x1_ext
y2_ext = 1/5 * x2_ext

plt.plot(x1_ext, y1_ext, '--', lw=2, c='#4A85F1', alpha=0.5)
plt.plot(x2_ext, y2_ext, '--', lw=2, c='#F1B74A', alpha=0.5)

plt.arrow(x2[-1], y2[-1], 0, y1[-1] - y2[-1], color='#F1B74A', linewidth=4, head_width=0, head_length=0, length_includes_head=True)
plt.scatter(x2[-1], y1[-1]+1.6, color='#F1B74A', marker='s', s=15)
plt.arrow(x2[-1], y1[-1]+3, 0, +1, color='#F1B74A', linestyle='solid', linewidth=4, head_width=0.3, head_length=1, length_includes_head=True)
plt.arrow(x1[0], y1[0], 0, y2[0] - y1[0]-1, color='#4A85F1', linewidth=4, head_width=0.3, head_length=1, length_includes_head=True)
plt.plot([x1[-1], x2[-1]], [y1[-1], y1[-1]], color='#4A85F1', linewidth=4)

plt.xlim(-11, 11)
plt.ylim(-20, 20)
plt.grid(True)
plt.xlabel('V (a.u.)')
plt.ylabel('I (a.u.)')

# Hide tick labels but keep ticks (and grid)
plt.gca().set_xticklabels([])
plt.gca().set_yticklabels([])

plt.plot([0, x1[-1]], [y1[-1], y1[-1]], color='k', linestyle=':', linewidth=2)
# plt.plot([x2[0], 0], [y1[0], y1[0]], color='k', linestyle=':', linewidth=2)

plt.show()