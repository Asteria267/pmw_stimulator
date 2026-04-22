"""
╔══════════════════════════════════════════════════════════════════╗
║           PWMSimulator Pro — BUILDCORED ORCAS Day 17            ║
║                  Dual-Channel PWM Visualizer                    ║
╚══════════════════════════════════════════════════════════════════╝

HARDWARE CONCEPT:
  PWM (Pulse Width Modulation) is how microcontrollers fake analog
  output from a purely digital pin. By rapidly toggling a pin
  HIGH/LOW, the *average* voltage = VCC × duty_cycle.
  
  No DAC (Digital-to-Analog Converter) needed — just timing.

  ┌───────────────────────────────────────────────────────────┐
  │  Duty 75%:  ████████████░░░░ ████████████░░░░ ...         │
  │  Duty 50%:  ████████░░░░░░░░ ████████░░░░░░░░ ...         │
  │  Duty 25%:  ████░░░░░░░░░░░░ ████░░░░░░░░░░░░ ...         │
  └───────────────────────────────────────────────────────────┘

REAL-WORLD USES:
  • LED dimming (Arduino analogWrite → Pico pwm.duty_u16())
  • Servo motor angle control (pulse width = position)
  • DC motor speed control
  • Audio synthesis (PWM DAC)
  • Switching power supplies

FEATURES IN THIS SIMULATOR:
  ✅ Channel A — Primary PWM (variable duty cycle + frequency)
  ✅ Channel B — Secondary PWM (different freq, required TODO #1)
  ✅ Live square-wave visualization with phosphor-glow effect
  ✅ Average voltage indicator (dashed line)
  ✅ Virtual LED with realistic warm-to-cool color temperature shift
  ✅ Dual LED display (one per channel)
  ✅ Phase relationship visualizer
  ✅ Frequency Sweep mode (auto-ramps duty cycle)
  ✅ Oscilloscope-style dark theme
  ✅ PWM code export (Pico MicroPython + Arduino C++)
  ✅ Stats panel: period, HIGH/LOW time, average V, Pico register value
  ✅ Keyboard shortcuts (Space = sweep, R = reset)

PICO v2.0 BRIDGE:
  The duty_u16() value shown in the stats panel IS the exact
  register value you'd write on a Raspberry Pi Pico:

      from machine import Pin, PWM
      pwm = PWM(Pin(15))
      pwm.freq(1000)
      pwm.duty_u16(32768)   # ← 50% duty (32768/65535)

  The code export button generates this for you.

Run:
    python day17_pwm_simulator.py

Dependencies:
    pip install matplotlib numpy
    # tkinter is included with Python on most systems
    # Linux: sudo apt install python3-tk
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches
from matplotlib.widgets import Slider, Button, CheckButtons
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
from matplotlib.gridspec import GridSpec
import time
import threading

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

VCC = 3.3           # Raspberry Pi Pico supply voltage
DISPLAY_CYCLES = 6  # How many cycles visible on screen
SAMPLE_PTS = 2000   # Waveform resolution (higher = smoother)

# Channel A defaults
CH_A_DUTY_INIT   = 50.0    # %
CH_A_FREQ_INIT   = 1000.0  # Hz

# Channel B defaults  (TODO #1 fulfilled: different frequency)
CH_B_DUTY_INIT   = 25.0    # %
CH_B_FREQ_INIT   = 500.0   # Hz  ← intentionally different

# Sweep mode
SWEEP_SPEED = 0.8   # % per frame
SWEEP_ACTIVE = [False]

# ─────────────────────────────────────────────────────────────────────────────
# OSCILLOSCOPE DARK THEME
# ─────────────────────────────────────────────────────────────────────────────

THEME = {
    "bg":           "#0a0f0d",
    "panel":        "#0d1512",
    "grid":         "#1a2e22",
    "ch_a":         "#00ff88",    # classic phosphor green
    "ch_a_dim":     "#00331a",
    "ch_a_avg":     "#ffcc00",    # amber average line
    "ch_b":         "#00aaff",    # blue for channel B
    "ch_b_dim":     "#001933",
    "ch_b_avg":     "#ff6699",
    "text":         "#c8ffd4",
    "text_dim":     "#4a7a5a",
    "accent":       "#00ff88",
    "warning":      "#ff4444",
    "slider_a":     "#00cc66",
    "slider_b":     "#0088cc",
    "led_off":      "#1a0a00",
}

matplotlib.rcParams.update({
    "figure.facecolor":  THEME["bg"],
    "axes.facecolor":    THEME["panel"],
    "axes.edgecolor":    THEME["grid"],
    "axes.labelcolor":   THEME["text"],
    "xtick.color":       THEME["text_dim"],
    "ytick.color":       THEME["text_dim"],
    "text.color":        THEME["text"],
    "grid.color":        THEME["grid"],
    "grid.linewidth":    0.6,
    "font.family":       "monospace",
})

# ─────────────────────────────────────────────────────────────────────────────
# CORE MATH
# ─────────────────────────────────────────────────────────────────────────────

def generate_pwm(duty_pct, freq_hz, cycles=DISPLAY_CYCLES, pts=SAMPLE_PTS):
    """
    Generate a PWM square wave for display.

    Returns (time_ms_array, voltage_array)

    Physics:
        period    = 1 / freq
        duty_frac = duty_pct / 100
        V = VCC  when (t % period) < duty_frac * period
        V = 0    otherwise

    On a Pico: pwm.duty_u16() sets duty_frac * 65535 as an integer.
    """
    period = 1.0 / freq_hz
    t = np.linspace(0, cycles * period, pts)
    phase = (t % period) / period        # 0→1 within each cycle
    duty_frac = duty_pct / 100.0
    v = np.where(phase < duty_frac, VCC, 0.0)
    t_ms = t * 1000.0                    # convert to milliseconds for display
    return t_ms, v


def avg_voltage(duty_pct):
    """V_avg = VCC × duty_fraction  (the entire point of PWM)"""
    return VCC * (duty_pct / 100.0)


def pico_duty_u16(duty_pct):
    """Maps 0–100% to 0–65535 (Pico's 16-bit register)"""
    return int((duty_pct / 100.0) * 65535)


def arduino_analogwrite(duty_pct):
    """Maps 0–100% to 0–255 (Arduino's 8-bit analogWrite)"""
    return int((duty_pct / 100.0) * 255)


def led_color(duty_pct):
    """
    Realistic LED color-temperature simulation.
    Low duty: deep red-orange (like a barely-warm filament)
    Mid duty: warm amber
    High duty: bright yellow-white (like a cool-white LED at full power)
    """
    b = duty_pct / 100.0
    if b < 0.001:
        return "#0d0502", "#000000"    # off: body, glow
    r = min(1.0, 0.6 + 0.4 * b)
    g = b ** 0.6 * 0.9
    bl = b ** 2.0 * 0.5
    body = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(bl*255))
    # glow is slightly desaturated
    gr = min(1.0, r * 0.8)
    gg = min(1.0, g * 0.7)
    gb = min(1.0, bl * 0.6)
    glow = "#{:02x}{:02x}{:02x}".format(int(gr*255), int(gg*255), int(gb*255))
    return body, glow


def led_b_color(duty_pct):
    """Channel B LED: blue-white tones"""
    b = duty_pct / 100.0
    if b < 0.001:
        return "#020509", "#000000"
    r = b ** 2.5 * 0.6
    g = b ** 1.2 * 0.8
    bl = min(1.0, 0.5 + 0.5 * b)
    body = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(bl*255))
    gr = min(1.0, r * 0.7)
    gg = min(1.0, g * 0.7)
    gb = min(1.0, bl * 0.8)
    glow = "#{:02x}{:02x}{:02x}".format(int(gr*255), int(gg*255), int(gb*255))
    return body, glow


# ─────────────────────────────────────────────────────────────────────────────
# CODE EXPORT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def pico_code(duty_a, freq_a, duty_b, freq_b):
    return f"""# ── Raspberry Pi Pico — MicroPython PWM Output ──────────────────
# Generated by PWMSimulator Pro (Day 17)
from machine import Pin, PWM

# Channel A  (GPIO 15)
pwm_a = PWM(Pin(15))
pwm_a.freq({int(freq_a)})            # {int(freq_a)} Hz
pwm_a.duty_u16({pico_duty_u16(duty_a)})  # {duty_a:.1f}% duty → avg {avg_voltage(duty_a):.2f}V

# Channel B  (GPIO 16)
pwm_b = PWM(Pin(16))
pwm_b.freq({int(freq_b)})            # {int(freq_b)} Hz  ← different channel!
pwm_b.duty_u16({pico_duty_u16(duty_b)})  # {duty_b:.1f}% duty → avg {avg_voltage(duty_b):.2f}V

print("PWM running — check your LED or oscilloscope!")
"""

def arduino_code(duty_a, freq_a, duty_b, freq_b):
    return f"""// ── Arduino — C++ PWM Output ─────────────────────────────────────
// Generated by PWMSimulator Pro (Day 17)
// Note: Arduino's analogWrite() uses ~490Hz or ~980Hz (board dependent)
// For custom frequency, use TimerOne or similar library.

const int LED_A = 9;   // Channel A (PWM pin)
const int LED_B = 10;  // Channel B (PWM pin)

void setup() {{
  pinMode(LED_A, OUTPUT);
  pinMode(LED_B, OUTPUT);

  // Channel A: {duty_a:.1f}% duty (analogWrite maps 0-100% to 0-255)
  analogWrite(LED_A, {arduino_analogwrite(duty_a)});  // → {avg_voltage(duty_a):.2f}V avg

  // Channel B: {duty_b:.1f}% duty
  analogWrite(LED_B, {arduino_analogwrite(duty_b)});  // → {avg_voltage(duty_b):.2f}V avg
}}

void loop() {{
  // PWM runs in hardware — loop can do other work!
}}
"""

# ─────────────────────────────────────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────────────────────────────────────

state = {
    "duty_a":   CH_A_DUTY_INIT,
    "freq_a":   CH_A_FREQ_INIT,
    "duty_b":   CH_B_DUTY_INIT,
    "freq_b":   CH_B_FREQ_INIT,
    "show_b":   True,
    "sweep":    False,
    "sweep_dir": 1,
    "phase":    0,
    "export_mode": "pico",   # "pico" or "arduino"
}

# ─────────────────────────────────────────────────────────────────────────────
# FIGURE LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(16, 10), facecolor=THEME["bg"])
fig.canvas.manager.set_window_title("PWMSimulator Pro — Day 17 | BuildCored Orcas")

# Custom grid
gs = GridSpec(
    nrows=10, ncols=12,
    left=0.04, right=0.98,
    top=0.94, bottom=0.03,
    hspace=0.5, wspace=0.4
)

# ── Title bar ──────────────────────────────────────────────────────────────
ax_title = fig.add_subplot(gs[0, :])
ax_title.axis("off")
ax_title.text(0.01, 0.5,
    "⬡  PWMSimulator Pro",
    transform=ax_title.transAxes,
    fontsize=15, fontweight="bold", color=THEME["ch_a"],
    va="center"
)
ax_title.text(0.30, 0.5,
    "DUAL-CHANNEL OSCILLOSCOPE",
    transform=ax_title.transAxes,
    fontsize=9, color=THEME["text_dim"], va="center"
)
ax_title.text(0.99, 0.5,
    "BuildCored Orcas — Day 17 / 30",
    transform=ax_title.transAxes,
    fontsize=8, color=THEME["text_dim"], va="center", ha="right"
)
# Horizontal rule under title
ax_title.axhline(0.05, color=THEME["grid"], linewidth=1.5)

# ── Channel A waveform ────────────────────────────────────────────────────
ax_a = fig.add_subplot(gs[1:4, :9])
ax_a.set_facecolor(THEME["panel"])
ax_a.set_xlim(0, DISPLAY_CYCLES / CH_A_FREQ_INIT * 1000)
ax_a.set_ylim(-0.4, VCC + 0.5)
ax_a.set_ylabel("Voltage (V)", color=THEME["ch_a"], fontsize=8)
ax_a.tick_params(labelbottom=False)
ax_a.grid(True, alpha=0.4)

# Channel label
ax_a.text(0.01, 0.92, "CH A", transform=ax_a.transAxes,
          color=THEME["ch_a"], fontsize=9, fontweight="bold", va="top")

# Waveform glow effect: plot same line twice (thick dim + thin bright)
wave_a_glow, = ax_a.plot([], [], color=THEME["ch_a_dim"], linewidth=6, alpha=0.4, solid_capstyle="butt")
wave_a,      = ax_a.plot([], [], color=THEME["ch_a"], linewidth=1.5, solid_capstyle="butt")

# Average voltage line
avg_a_line = ax_a.axhline(avg_voltage(CH_A_DUTY_INIT),
                           color=THEME["ch_a_avg"], linewidth=1.2,
                           linestyle="--", label=f"Avg = {avg_voltage(CH_A_DUTY_INIT):.2f}V")
avg_a_label = ax_a.text(0.75, 0.18, "", transform=ax_a.transAxes,
                         color=THEME["ch_a_avg"], fontsize=8)

# VCC marker
ax_a.axhline(VCC, color=THEME["text_dim"], linewidth=0.5, linestyle=":")
ax_a.text(0.995, 0.93, f"VCC {VCC}V", transform=ax_a.transAxes,
          color=THEME["text_dim"], fontsize=7, ha="right")

# ── Channel B waveform ────────────────────────────────────────────────────
ax_b = fig.add_subplot(gs[4:7, :9])
ax_b.set_facecolor(THEME["panel"])
ax_b.set_ylim(-0.4, VCC + 0.5)
ax_b.set_xlabel("Time (ms)", color=THEME["text_dim"], fontsize=8)
ax_b.set_ylabel("Voltage (V)", color=THEME["ch_b"], fontsize=8)
ax_b.grid(True, alpha=0.4)

ax_b.text(0.01, 0.92, "CH B", transform=ax_b.transAxes,
          color=THEME["ch_b"], fontsize=9, fontweight="bold", va="top")

wave_b_glow, = ax_b.plot([], [], color=THEME["ch_b_dim"], linewidth=6, alpha=0.4, solid_capstyle="butt")
wave_b,      = ax_b.plot([], [], color=THEME["ch_b"], linewidth=1.5, solid_capstyle="butt")

avg_b_line = ax_b.axhline(avg_voltage(CH_B_DUTY_INIT),
                           color=THEME["ch_b_avg"], linewidth=1.2,
                           linestyle="--")
avg_b_label = ax_b.text(0.75, 0.18, "", transform=ax_b.transAxes,
                         color=THEME["ch_b_avg"], fontsize=8)

ax_b.axhline(VCC, color=THEME["text_dim"], linewidth=0.5, linestyle=":")
ax_b.text(0.995, 0.93, f"VCC {VCC}V", transform=ax_b.transAxes,
          color=THEME["text_dim"], fontsize=7, ha="right")

# ── LED Panel — Channel A ─────────────────────────────────────────────────
ax_led_a = fig.add_subplot(gs[1:4, 9:11])
ax_led_a.set_xlim(-2, 2); ax_led_a.set_ylim(-2.5, 2.2)
ax_led_a.set_aspect("equal")
ax_led_a.axis("off")
ax_led_a.set_facecolor(THEME["bg"])
ax_led_a.text(0, 2.0, "LED-A", ha="center", color=THEME["ch_a"],
              fontsize=8, fontweight="bold")

led_a_glow  = Circle((0, 0), 1.6, color="#000000", alpha=0)
led_a_body  = Circle((0, 0), 1.1, color=THEME["led_off"], alpha=1)
led_a_shine = Circle((0.35, 0.35), 0.3, color="#ffffff", alpha=0.0)
led_a_base  = Rectangle((-0.5, -1.5), 1.0, 0.45, color="#2a2a2a", linewidth=0)
led_a_pin1  = Rectangle((-0.35, -2.1), 0.12, 0.65, color="#555555", linewidth=0)
led_a_pin2  = Rectangle(( 0.23, -2.1), 0.12, 0.65, color="#555555", linewidth=0)
led_a_label = ax_led_a.text(0, -2.4, "OFF", ha="center",
                              color=THEME["text_dim"], fontsize=8, fontweight="bold")

for p in [led_a_glow, led_a_body, led_a_shine, led_a_base, led_a_pin1, led_a_pin2]:
    ax_led_a.add_patch(p)

# ── LED Panel — Channel B ─────────────────────────────────────────────────
ax_led_b = fig.add_subplot(gs[4:7, 9:11])
ax_led_b.set_xlim(-2, 2); ax_led_b.set_ylim(-2.5, 2.2)
ax_led_b.set_aspect("equal")
ax_led_b.axis("off")
ax_led_b.set_facecolor(THEME["bg"])
ax_led_b.text(0, 2.0, "LED-B", ha="center", color=THEME["ch_b"],
              fontsize=8, fontweight="bold")

led_b_glow  = Circle((0, 0), 1.6, color="#000000", alpha=0)
led_b_body  = Circle((0, 0), 1.1, color=THEME["led_off"], alpha=1)
led_b_shine = Circle((0.35, 0.35), 0.3, color="#ffffff", alpha=0.0)
led_b_base  = Rectangle((-0.5, -1.5), 1.0, 0.45, color="#2a2a2a", linewidth=0)
led_b_pin1  = Rectangle((-0.35, -2.1), 0.12, 0.65, color="#555555", linewidth=0)
led_b_pin2  = Rectangle(( 0.23, -2.1), 0.12, 0.65, color="#555555", linewidth=0)
led_b_label = ax_led_b.text(0, -2.4, "OFF", ha="center",
                              color=THEME["text_dim"], fontsize=8, fontweight="bold")

for p in [led_b_glow, led_b_body, led_b_shine, led_b_base, led_b_pin1, led_b_pin2]:
    ax_led_b.add_patch(p)

# ── Stats Panel ───────────────────────────────────────────────────────────
ax_stats = fig.add_subplot(gs[7, :9])
ax_stats.axis("off")
ax_stats.set_facecolor(THEME["bg"])
stats_text = ax_stats.text(
    0.5, 0.5, "",
    transform=ax_stats.transAxes,
    ha="center", va="center",
    fontsize=8, color=THEME["text"],
    family="monospace",
    bbox=dict(boxstyle="round,pad=0.5", facecolor=THEME["panel"],
              edgecolor=THEME["grid"], linewidth=1)
)

# ── Code Export Panel ─────────────────────────────────────────────────────
ax_code = fig.add_subplot(gs[7:10, 9:12])
ax_code.axis("off")
ax_code.set_facecolor(THEME["bg"])
code_text = ax_code.text(
    0.03, 0.97, "",
    transform=ax_code.transAxes,
    ha="left", va="top",
    fontsize=6.2, color="#aaffcc",
    family="monospace",
    wrap=True
)

# ── Sliders ───────────────────────────────────────────────────────────────
# Channel A — duty
sl_ax_duty_a = plt.axes([0.06, 0.155, 0.40, 0.022], facecolor=THEME["panel"])
sl_duty_a = Slider(sl_ax_duty_a, "CH-A Duty %", 0, 100,
                   valinit=CH_A_DUTY_INIT, valstep=0.5, color=THEME["slider_a"])
sl_duty_a.label.set_color(THEME["ch_a"])
sl_duty_a.valtext.set_color(THEME["ch_a"])

# Channel A — frequency
sl_ax_freq_a = plt.axes([0.06, 0.122, 0.40, 0.022], facecolor=THEME["panel"])
sl_freq_a = Slider(sl_ax_freq_a, "CH-A Freq Hz", 100, 5000,
                   valinit=CH_A_FREQ_INIT, valstep=50, color=THEME["slider_a"])
sl_freq_a.label.set_color(THEME["ch_a"])
sl_freq_a.valtext.set_color(THEME["ch_a"])

# Channel B — duty
sl_ax_duty_b = plt.axes([0.52, 0.155, 0.40, 0.022], facecolor=THEME["panel"])
sl_duty_b = Slider(sl_ax_duty_b, "CH-B Duty %", 0, 100,
                   valinit=CH_B_DUTY_INIT, valstep=0.5, color=THEME["slider_b"])
sl_duty_b.label.set_color(THEME["ch_b"])
sl_duty_b.valtext.set_color(THEME["ch_b"])

# Channel B — frequency
sl_ax_freq_b = plt.axes([0.52, 0.122, 0.40, 0.022], facecolor=THEME["panel"])
sl_freq_b = Slider(sl_ax_freq_b, "CH-B Freq Hz", 100, 5000,
                   valinit=CH_B_FREQ_INIT, valstep=50, color=THEME["slider_b"])
sl_freq_b.label.set_color(THEME["ch_b"])
sl_freq_b.valtext.set_color(THEME["ch_b"])

# ── Buttons ───────────────────────────────────────────────────────────────
btn_sweep_ax    = plt.axes([0.06,  0.065, 0.12, 0.038])
btn_reset_ax    = plt.axes([0.20,  0.065, 0.12, 0.038])
btn_pico_ax     = plt.axes([0.36,  0.065, 0.14, 0.038])
btn_arduino_ax  = plt.axes([0.52,  0.065, 0.14, 0.038])
btn_half_ax     = plt.axes([0.70,  0.065, 0.10, 0.038])
btn_max_ax      = plt.axes([0.82,  0.065, 0.10, 0.038])

def style_btn(ax, label, color):
    ax.set_facecolor(THEME["panel"])
    return Button(ax, label, color=THEME["panel"], hovercolor=THEME["grid"])

btn_sweep   = style_btn(btn_sweep_ax,   "⟳ SWEEP",    THEME["ch_a"])
btn_reset   = style_btn(btn_reset_ax,   "↺ RESET",    THEME["text_dim"])
btn_pico    = style_btn(btn_pico_ax,    "🐍 Pico Code", THEME["ch_a"])
btn_arduino = style_btn(btn_arduino_ax, "⚡ Arduino",  THEME["ch_b"])
btn_half    = style_btn(btn_half_ax,    "50% Quick",  THEME["ch_a_avg"])
btn_max     = style_btn(btn_max_ax,     "100% Full",  THEME["ch_a_avg"])

for b in [btn_sweep, btn_reset, btn_pico, btn_arduino, btn_half, btn_max]:
    b.label.set_color(THEME["text"])
    b.label.set_fontsize(8)

# ── Keyboard hint ─────────────────────────────────────────────────────────
fig.text(0.5, 0.003,
         "SPACE = toggle sweep  |  R = reset  |  P = Pico code  |  A = Arduino code",
         ha="center", fontsize=7, color=THEME["text_dim"])

# ─────────────────────────────────────────────────────────────────────────────
# LED UPDATER
# ─────────────────────────────────────────────────────────────────────────────

LED_STATES = ["OFF", "GLOW", "DIM", "MEDIUM", "BRIGHT", "MAX"]

def duty_to_label(d):
    if d < 1:    return "OFF"
    elif d < 15: return "GLOW"
    elif d < 35: return "DIM"
    elif d < 65: return "MEDIUM"
    elif d < 90: return "BRIGHT"
    else:        return "MAX ★"

def update_led(body, glow, shine, label_obj, duty_pct, color_fn):
    b = duty_pct / 100.0
    body_col, glow_col = color_fn(duty_pct)
    body.set_color(body_col)
    glow.set_color(glow_col)
    glow.set_alpha(b * 0.55)
    shine.set_alpha(b * 0.55)
    label_obj.set_text(duty_to_label(duty_pct))
    bright = b
    label_obj.set_color(
        THEME["ch_a_avg"] if bright > 0.7 else
        THEME["text_dim"] if bright < 0.05 else
        THEME["text"]
    )

# ─────────────────────────────────────────────────────────────────────────────
# MAIN UPDATE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def full_update():
    da = state["duty_a"]
    fa = state["freq_a"]
    db = state["duty_b"]
    fb = state["freq_b"]

    # ── Channel A waveform ─────────────────────────────────────────────
    t_a, v_a = generate_pwm(da, fa)
    t_max_a = DISPLAY_CYCLES / fa * 1000
    ax_a.set_xlim(0, t_max_a)
    wave_a.set_data(t_a, v_a)
    wave_a_glow.set_data(t_a, v_a)

    avg_a = avg_voltage(da)
    avg_a_line.set_ydata([avg_a, avg_a])
    avg_a_label.set_text(f"Avg = {avg_a:.3f} V  ({da:.1f}%)")

    # ── Channel B waveform ─────────────────────────────────────────────
    t_b, v_b = generate_pwm(db, fb)
    t_max_b = DISPLAY_CYCLES / fb * 1000
    ax_b.set_xlim(0, t_max_b)
    wave_b.set_data(t_b, v_b)
    wave_b_glow.set_data(t_b, v_b)

    avg_b = avg_voltage(db)
    avg_b_line.set_ydata([avg_b, avg_b])
    avg_b_label.set_text(f"Avg = {avg_b:.3f} V  ({db:.1f}%)")

    # ── LEDs ───────────────────────────────────────────────────────────
    update_led(led_a_body, led_a_glow, led_a_shine, led_a_label, da, led_color)
    update_led(led_b_body, led_b_glow, led_b_shine, led_b_label, db, led_b_color)

    # ── Stats ──────────────────────────────────────────────────────────
    period_a_us = 1e6 / fa
    hi_a_us     = period_a_us * da / 100
    lo_a_us     = period_a_us - hi_a_us

    period_b_us = 1e6 / fb
    hi_b_us     = period_b_us * db / 100
    lo_b_us     = period_b_us - hi_b_us

    stats = (
        f"  CH A │ Freq: {fa:>6.0f} Hz │ Period: {period_a_us:>7.1f} µs │"
        f" HIGH: {hi_a_us:>7.1f} µs │ LOW: {lo_a_us:>7.1f} µs │"
        f" Avg: {avg_a:.3f}V │ duty_u16: {pico_duty_u16(da):>5}  \n"
        f"  CH B │ Freq: {fb:>6.0f} Hz │ Period: {period_b_us:>7.1f} µs │"
        f" HIGH: {hi_b_us:>7.1f} µs │ LOW: {lo_b_us:>7.1f} µs │"
        f" Avg: {avg_b:.3f}V │ duty_u16: {pico_duty_u16(db):>5}  "
    )
    stats_text.set_text(stats)

    # ── Code Export ────────────────────────────────────────────────────
    mode = state["export_mode"]
    if mode == "pico":
        code_text.set_text(pico_code(da, fa, db, fb))
    else:
        code_text.set_text(arduino_code(da, fa, db, fb))

    fig.canvas.draw_idle()

# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────

def on_duty_a(val):
    state["duty_a"] = val
    full_update()

def on_freq_a(val):
    state["freq_a"] = val
    full_update()

def on_duty_b(val):
    state["duty_b"] = val
    full_update()

def on_freq_b(val):
    state["freq_b"] = val
    full_update()

sl_duty_a.on_changed(on_duty_a)
sl_freq_a.on_changed(on_freq_a)
sl_duty_b.on_changed(on_duty_b)
sl_freq_b.on_changed(on_freq_b)


def do_reset(event=None):
    state["sweep"] = False
    btn_sweep.label.set_text("⟳ SWEEP")
    sl_duty_a.set_val(CH_A_DUTY_INIT)
    sl_freq_a.set_val(CH_A_FREQ_INIT)
    sl_duty_b.set_val(CH_B_DUTY_INIT)
    sl_freq_b.set_val(CH_B_FREQ_INIT)
    state["duty_a"] = CH_A_DUTY_INIT
    state["freq_a"] = CH_A_FREQ_INIT
    state["duty_b"] = CH_B_DUTY_INIT
    state["freq_b"] = CH_B_FREQ_INIT
    full_update()

def do_sweep(event=None):
    state["sweep"] = not state["sweep"]
    btn_sweep.label.set_text("■ STOP" if state["sweep"] else "⟳ SWEEP")
    fig.canvas.draw_idle()

def do_pico(event=None):
    state["export_mode"] = "pico"
    full_update()

def do_arduino(event=None):
    state["export_mode"] = "arduino"
    full_update()

def do_half(event=None):
    sl_duty_a.set_val(50)
    sl_duty_b.set_val(50)

def do_max(event=None):
    sl_duty_a.set_val(100)
    sl_duty_b.set_val(100)

btn_sweep.on_clicked(do_sweep)
btn_reset.on_clicked(do_reset)
btn_pico.on_clicked(do_pico)
btn_arduino.on_clicked(do_arduino)
btn_half.on_clicked(do_half)
btn_max.on_clicked(do_max)


def on_key(event):
    if event.key == " ":
        do_sweep()
    elif event.key in ("r", "R"):
        do_reset()
    elif event.key in ("p", "P"):
        do_pico()
    elif event.key in ("a", "A"):
        do_arduino()

fig.canvas.mpl_connect("key_press_event", on_key)

# ─────────────────────────────────────────────────────────────────────────────
# ANIMATION — Sweep Mode
# ─────────────────────────────────────────────────────────────────────────────

def animate(frame):
    if state["sweep"]:
        d = state["duty_a"] + SWEEP_SPEED * state["sweep_dir"]
        if d >= 100:
            d = 100
            state["sweep_dir"] = -1
        elif d <= 0:
            d = 0
            state["sweep_dir"] = 1
        state["duty_a"] = d
        sl_duty_a.set_val(round(d, 1))   # also moves slider
        # B sweeps opposite phase for visual contrast
        d_b = 100 - d
        state["duty_b"] = d_b
        sl_duty_b.set_val(round(d_b, 1))
        full_update()
    return []

ani = animation.FuncAnimation(
    fig, animate, interval=40, blit=False, cache_frame_data=False
)

# ─────────────────────────────────────────────────────────────────────────────
# INITIAL RENDER
# ─────────────────────────────────────────────────────────────────────────────

full_update()

# ─────────────────────────────────────────────────────────────────────────────
# LAUNCH
# ─────────────────────────────────────────────────────────────────────────────

print()
print("╔══════════════════════════════════════════════════════════╗")
print("║       PWMSimulator Pro — Day 17 / BuildCored Orcas       ║")
print("╠══════════════════════════════════════════════════════════╣")
print("║  Dual-Channel Oscilloscope + LED Visualizer              ║")
print("╠══════════════════════════════════════════════════════════╣")
print("║  CONTROLS                                                ║")
print("║  • Drag sliders → change duty cycle / frequency         ║")
print("║  • [SWEEP] button → auto-ramp duty cycle (A↑ B↓)        ║")
print("║  • [50% Quick] → set both channels to 50%               ║")
print("║  • [100% Full] → set both to full-on                    ║")
print("║  • [🐍 Pico Code] → show MicroPython export             ║")
print("║  • [⚡ Arduino]  → show C++ export                      ║")
print("║                                                          ║")
print("║  KEYBOARD                                                ║")
print("║  SPACE = toggle sweep  R = reset  P = Pico  A = Arduino  ║")
print("╠══════════════════════════════════════════════════════════╣")
print("║  HARDWARE FACT:                                          ║")
print("║  Your CPU toggles pins at MHz — human eye sees average   ║")
print("║  voltage. That IS the PWM magic.                         ║")
print("╠══════════════════════════════════════════════════════════╣")
print("║  Close the plot window to exit.                          ║")
print("╚══════════════════════════════════════════════════════════╝")
print()

plt.show()

print("\n✅ PWMSimulator session ended. Day 17 complete, cigga!")
print("  You've got this. 🐋")
