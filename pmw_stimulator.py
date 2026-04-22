# PWMForge Elite v2 — Rose Quartz Edition
# Premium PWM Simulator
# Run:
#   pip install matplotlib numpy
#   python pwmforge_rose.py

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.patches import Circle, FancyBboxPatch
import matplotlib.animation as animation

# ─────────────────────────────────────────────────────
# THEME : ROSE QUARTZ
# ─────────────────────────────────────────────────────
BG          = "#0d0911"
PANEL       = "#17111d"
GRID        = "#2b2033"
TEXT        = "#f7d9ea"
DIM         = "#9b7f92"

PINK        = "#ff4fa3"
PINK_GLOW   = "#ff8fc4"
ROSE        = "#ff7ab8"
GOLD        = "#ffd6e7"
SOFT        = "#ffc1dd"

GREEN       = "#8bffb2"

VCC = 5.0
INIT_DUTY = 50.0
INIT_FREQ = 1000.0

# ─────────────────────────────────────────────────────
# SIGNAL ENGINE
# ─────────────────────────────────────────────────────
def pwm_wave(duty, freq, cycles=4, pts=2600):
    period = 1.0 / freq
    t = np.linspace(0, cycles * period, pts)
    phase = (t % period) / period
    v = np.where(phase < duty / 100.0, VCC, 0.0)
    return t * 1000, v

def avg_voltage(duty):
    return VCC * duty / 100.0

def rc_filter(sig, alpha=0.03):
    out = np.zeros_like(sig)
    for i in range(1, len(sig)):
        out[i] = out[i-1] + alpha * (sig[i] - out[i-1])
    return out

def pico_val(duty):
    return int(65535 * duty / 100)

def arduino_val(duty):
    return int(255 * duty / 100)

def led_color(duty):
    b = duty / 100.0
    r = min(1.0, 0.6 + 0.4 * b)
    g = min(1.0, 0.15 + 0.45 * b)
    bl = min(1.0, 0.4 + 0.6 * b)
    return "#{:02x}{:02x}{:02x}".format(
        int(r * 255), int(g * 255), int(bl * 255)
    )

# ─────────────────────────────────────────────────────
# WINDOW
# ─────────────────────────────────────────────────────
fig = plt.figure(figsize=(15, 8.8), facecolor=BG)
fig.canvas.manager.set_window_title("PWMForge Elite v2 — Rose Quartz")

# waveform area
ax = fig.add_axes([0.05, 0.32, 0.64, 0.58], facecolor=PANEL)

# side panel
side = fig.add_axes([0.73, 0.32, 0.23, 0.58], facecolor=PANEL)
side.set_xlim(0, 1)
side.set_ylim(0, 1)
side.axis("off")

# sliders
ax_duty = fig.add_axes([0.08, 0.20, 0.54, 0.028], facecolor=PANEL)
ax_freq = fig.add_axes([0.08, 0.14, 0.54, 0.028], facecolor=PANEL)

# buttons
ax_btn_reset = fig.add_axes([0.73, 0.18, 0.10, 0.05])
ax_btn_sweep = fig.add_axes([0.85, 0.18, 0.10, 0.05])

# ─────────────────────────────────────────────────────
# WAVEFORM STYLE
# ─────────────────────────────────────────────────────
for s in ax.spines.values():
    s.set_color(GRID)

ax.tick_params(colors=DIM)
ax.grid(True, color=GRID, linestyle="--", linewidth=0.7)

ax.set_xlabel("Time (ms)", color=DIM)
ax.set_ylabel("Voltage (V)", color=DIM)

ax.set_title(
    "PWM Signal + Analog RC Smoothing",
    color=PINK,
    fontsize=14,
    fontweight="bold",
    loc="left"
)

# initial data
t, v = pwm_wave(INIT_DUTY, INIT_FREQ)
filt = rc_filter(v)

# glow layers
wave_glow, = ax.plot(t, v, color=PINK_GLOW, lw=6, alpha=0.18)
wave_line, = ax.plot(t, v, color=PINK, lw=2.2)

rc_glow, = ax.plot(t, filt, color=SOFT, lw=5, alpha=0.16)
rc_line, = ax.plot(t, filt, color=GOLD, lw=2.0)

avg_line = ax.axhline(avg_voltage(INIT_DUTY),
                      color=ROSE, lw=1.7, ls="--")

ax.legend(
    ["PWM", "RC Output"],
    facecolor=PANEL,
    edgecolor=GRID,
    labelcolor=TEXT,
    loc="upper right"
)

# ─────────────────────────────────────────────────────
# SIDE PANEL UI
# ─────────────────────────────────────────────────────
side.text(0.07, 0.95, "Rose Quartz Metrics",
          color=PINK, fontsize=13, fontweight="bold", va="top")

metrics = side.text(0.07, 0.76, "",
                    color=TEXT,
                    fontsize=10,
                    family="monospace",
                    va="top")

codebox = FancyBboxPatch(
    (0.05, 0.32), 0.90, 0.22,
    boxstyle="round,pad=0.02",
    facecolor="#120d18",
    edgecolor=GRID
)
side.add_patch(codebox)

code = side.text(0.08, 0.51, "",
                 color=SOFT,
                 fontsize=8.6,
                 family="monospace",
                 va="top")

# LED
halo = Circle((0.50, 0.16), 0.14, color=PINK, alpha=0.0)
led = Circle((0.50, 0.16), 0.085, color="#220011")
side.add_patch(halo)
side.add_patch(led)

side.text(0.50, 0.03, "Virtual LED",
          ha="center", color=DIM, fontsize=8)

# ─────────────────────────────────────────────────────
# CONTROLS
# ─────────────────────────────────────────────────────
sl_duty = Slider(ax_duty, "Duty %", 0, 100,
                 valinit=INIT_DUTY,
                 valstep=0.5,
                 color=PINK)

sl_freq = Slider(ax_freq, "Freq Hz", 100, 5000,
                 valinit=INIT_FREQ,
                 valstep=50,
                 color=ROSE)

for s in [sl_duty, sl_freq]:
    s.label.set_color(TEXT)
    s.valtext.set_color(PINK)

btn_reset = Button(ax_btn_reset, "Reset",
                   color=PANEL, hovercolor=GRID)
btn_sweep = Button(ax_btn_sweep, "Sweep",
                   color=PANEL, hovercolor=GRID)

btn_reset.label.set_color(TEXT)
btn_sweep.label.set_color(TEXT)

# ─────────────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────────────
state = {
    "sweep": False,
    "dir": 1
}

# ─────────────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────────────
def refresh(_=None):
    duty = sl_duty.val
    freq = sl_freq.val

    t, v = pwm_wave(duty, freq)

    alpha = min(0.15, (220 / freq) * 0.03)
    filt = rc_filter(v, alpha=max(alpha, 0.008))

    wave_glow.set_data(t, v)
    wave_line.set_data(t, v)

    rc_glow.set_data(t, filt)
    rc_line.set_data(t, filt)

    ax.set_xlim(0, t[-1])
    ax.set_ylim(-0.3, VCC + 0.5)

    avg = avg_voltage(duty)
    avg_line.set_ydata([avg, avg])

    period = 1000 / freq
    high = period * duty / 100
    low = period - high

    metrics.set_text(
        f"Duty      : {duty:6.1f}%\n"
        f"Freq      : {freq:6.0f} Hz\n"
        f"Period    : {period:6.3f} ms\n"
        f"HIGH time : {high:6.3f} ms\n"
        f"LOW time  : {low:6.3f} ms\n"
        f"Avg Volt  : {avg:6.2f} V"
    )

    code.set_text(
        f"Arduino:\n"
        f"analogWrite(pin,{arduino_val(duty)})\n\n"
        f"Pico:\n"
        f"pwm.duty_u16({pico_val(duty)})"
    )

    c = led_color(duty)
    led.set_color(c)
    halo.set_color(c)
    halo.set_alpha((duty / 100) * 0.55)

    fig.canvas.draw_idle()

# ─────────────────────────────────────────────────────
# BUTTONS
# ─────────────────────────────────────────────────────
def reset(event):
    state["sweep"] = False
    btn_sweep.label.set_text("Sweep")
    sl_duty.set_val(INIT_DUTY)
    sl_freq.set_val(INIT_FREQ)

def toggle_sweep(event):
    state["sweep"] = not state["sweep"]
    btn_sweep.label.set_text("Stop" if state["sweep"] else "Sweep")
    fig.canvas.draw_idle()

btn_reset.on_clicked(reset)
btn_sweep.on_clicked(toggle_sweep)

# ─────────────────────────────────────────────────────
# ANIMATION
# ─────────────────────────────────────────────────────
def animate(frame):
    if state["sweep"]:
        d = sl_duty.val + state["dir"] * 1.0

        if d >= 100:
            d = 100
            state["dir"] = -1
        elif d <= 0:
            d = 0
            state["dir"] = 1

        sl_duty.set_val(d)

    return []

ani = animation.FuncAnimation(
    fig,
    animate,
    interval=35,
    blit=False,
    cache_frame_data=False
)

# ─────────────────────────────────────────────────────
# CALLBACKS
# ─────────────────────────────────────────────────────
sl_duty.on_changed(refresh)
sl_freq.on_changed(refresh)

# keyboard shortcuts
def on_key(event):
    if event.key == " ":
        toggle_sweep(None)
    elif event.key.lower() == "r":
        reset(None)

fig.canvas.mpl_connect("key_press_event", on_key)

# ─────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────
fig.text(0.5, 0.965,
         "PWMForge Elite v2",
         ha="center",
         color=PINK,
         fontsize=21,
         fontweight="bold",
         family="monospace")

fig.text(0.5, 0.938,
         "Rose Quartz Edition • Elegant PWM Engineering • BUILDCORED ORCAS",
         ha="center",
         color=DIM,
         fontsize=8)

# start
refresh()
plt.show()
