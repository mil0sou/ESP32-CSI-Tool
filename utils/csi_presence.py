import sys, re, time, threading
import numpy as np
import matplotlib.pyplot as plt
from collections import deque

WINDOW = 20           # ~0.5 s si ~100 Hz, ~3 s si ~15 Hz — voir print de rate
HISTORY = 300
FIXED_THRESHOLD = 2.2
DRAW_HZ = 10

csi_re = re.compile(r'\[([-\d\s]+)\]')

sub_matrix = deque(maxlen=WINDOW)     # les WINDOW dernières trames de sous-porteuses
motion_history = deque(maxlen=HISTORY)
presence_history = deque(maxlen=HISTORY)
rate_counter = [0]

lock = threading.Lock()

def reader():
    for line in sys.stdin:
        if not line.startswith('CSI_DATA'):
            continue
        m = csi_re.search(line)
        if not m:
            continue
        vals = np.fromstring(m.group(1), sep=' ', dtype=np.int32)
        if len(vals) < 2:
            continue
        pairs = vals[:len(vals)//2*2].reshape(-1, 2)
        amps = np.sqrt(pairs[:, 0]**2 + pairs[:, 1]**2)
        # garde uniquement les sous-porteuses actives (non nulles en moyenne)
        # on stocke tout, on filtrera au calcul
        with lock:
            sub_matrix.append(amps)
            rate_counter[0] += 1
            if len(sub_matrix) >= 10:
                mat = np.array(sub_matrix)          # (T, N_sub)
                std_per_sub = mat.std(axis=0)       # écart-type temporel par sous-porteuse
                active = std_per_sub[mat.mean(axis=0) > 0]  # ignore les nulles
                if len(active) > 0:
                    motion = float(active.mean())   # « tremblement » moyen des actives
                else:
                    motion = 0.0
                motion_history.append(motion)
                presence_history.append(motion > FIXED_THRESHOLD)

t = threading.Thread(target=reader, daemon=True)
t.start()

# print du taux CSI/s + motion 2×/s
def stats_printer():
    last = time.time()
    while True:
        time.sleep(0.5)
        with lock:
            rate = rate_counter[0] / (time.time() - last)
            rate_counter[0] = 0
            cur = motion_history[-1] if motion_history else 0
        last = time.time()
        print(f'  rate={rate:.1f}Hz  motion={cur:.2f}', flush=True)

threading.Thread(target=stats_printer, daemon=True).start()

plt.ion()
fig, ax = plt.subplots(figsize=(10, 4))
line_mot, = ax.plot([], [], 'g-', lw=1, label='motion')
line_thr, = ax.plot([], [], 'r--', lw=1, label=f'seuil={FIXED_THRESHOLD}')
ax.set_title("Detection (rouge = presence)")
ax.set_xlabel("Trames"); ax.set_ylabel("Motion (std moyenne par sous-porteuse)")
ax.legend(loc='upper right')

period = 1.0 / DRAW_HZ
while plt.fignum_exists(fig.number):
    tic = time.time()
    with lock:
        mot = list(motion_history)
        pres = np.array(presence_history, dtype=bool)
    if mot:
        line_mot.set_data(np.arange(len(mot)), mot)
        line_thr.set_data([0, HISTORY], [FIXED_THRESHOLD, FIXED_THRESHOLD])
        ax.set_xlim(0, HISTORY); ax.relim(); ax.autoscale_view(scaley=True)
        for coll in list(ax.collections):
            coll.remove()
        if pres.any():
            ax.fill_between(np.arange(len(pres)), 0, ax.get_ylim()[1],
                            where=pres, color='red', alpha=0.25, step='mid')
    fig.canvas.draw_idle(); fig.canvas.flush_events()
    dt = time.time() - tic
    if dt < period: time.sleep(period - dt)
