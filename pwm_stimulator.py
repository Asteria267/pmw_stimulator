"""
╔══════════════════════════════════════════════════════════════════╗
║        PWMForge Elite v3 — Rose Quartz Edition                  ║
║        Dual-Channel PWM Oscilloscope + RC Filter + Phase View   ║
║        BuildCored Orcas — Day 17                                ║
╚══════════════════════════════════════════════════════════════════╝

WHAT IS PWM?
────────────
A microcontroller pin is purely DIGITAL: fully ON (3.3V) or fully OFF (0V).
PWM tricks it into "faking" analog output by switching very fast.

  Duty Cycle % = (Time HIGH / Period) × 100
  Average Voltage = VCC × (Duty / 100)

  At 1000 Hz, 50% duty → pin flips 1000×/sec → LED sees 1.65V average

DUAL CHANNEL (required TODO):
  CH1 → 1000 Hz  (LED dimming, analogWrite)
  CH2 →  300 Hz  (servo / motor control) — DIFFERENT frequency

RC FILTER (bonus hardware concept):
  A resistor + capacitor smooths PWM into a true analog voltage.
  Lower frequency = more ripple visible on the output.
  Higher frequency = cleaner output (capacitor has time to charge/discharge less).

Run:
    pip install matplotlib numpy
    python pwmforge_rose.py

Keyboard shortcuts:
    SPACE → toggle sweep
    R     → reset all
    1     → focus Channel 1
    2     → focus Channel 2
"""

# ── IMPORTS ────────────────────────────────────────────────────────────────
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle, FancyArrowPatch
from matplotlib.lines import Line2D

# ══════════════════════════════════════════════════════════════════════════
# ROSE QUARTZ THEME  (your original palette — expanded)
# ══════════════════════════════════════════════════════════════════════════
BG        = "#0d0911"
PANEL     = "#17111d"
PANEL2    = "#1f1628"
GRID      = "#2b2033"
TEXT      = "#f7d9ea"
DIM       = "#9b7f92"
DIMMER    = "#4a3545"

# Channel 1 — hot pink
PINK      = "#ff4fa3"
PINK_GLOW = "#ff8fc4"
PINK_DIM  = "#3d0f24"

# Channel 2 — violet/lavender
VIOLET    = "#b060ff"
VIOL_GLOW = "#d0a0ff"
VIOL_DIM  = "#1e0838"

# Average lines
AVG_PINK  = "#ffd6e7"
AVG_VIOL  = "#e0c0ff"

# RC filter outputs
RC_PINK   = "#ff9fcc"
RC_VIOL   = "#c890ff"

# Gold accent
GOLD      = "#ffd700"
SOFT      = "#ffc1dd"

VCC = 3.3          # Pico voltage (3.3V)
DISPLAY_CYCLES = 4
SAMPLE_PTS = 2000

# ── Starting values ────────────────────────────────────────────────────────
CH1_FREQ      = 1000.0   # Hz — LED dimming
CH2_FREQ      = 300.0    # Hz — servo/motor (DIFFERENT frequency = TODO done)
CH1_DUTY_INIT = 50.0
CH2_DUTY_INIT = 25.0

# ══════════════════════════════════════════════════════════════════════════
# SIGNAL ENGINE
# ══════════════════════════════════════════════════════════════════════════

def pwm_wave(duty, freq, cycles=DISPLAY_CYCLES, pts=SAMPLE_PTS):
    """Generate a PWM square wave. Returns (time_ms, voltage)."""
    period = 1.0 / freq
    t = np.linspace(0, cycles * period, pts)
    phase = (t % period) / period
    v = np.where(phase < duty / 100.0, VCC, 0.0)
    return t * 1000.0, v   # time in ms


def rc_filter(v, freq, rc_constant=0.0008):
    """
    Simulate a low-pass RC filter on the PWM signal.

    The RC time constant controls how much smoothing happens:
    - Small RC → filter responds fast → more ripple visible
    - Large RC → filter responds slow → smoother output

    At lower frequencies (CH2 = 300 Hz) you see MORE ripple
    because each period is longer relative to the RC constant.
    This is real hardware behaviour — great to demonstrate!

    alpha = dt / (RC + dt)   ← discrete approximation of RC low-pass
    """
    period = 1.0 / freq
    total_time = DISPLAY_CYCLES * period
    dt = total_time / SAMPLE_PTS
    alpha = dt / (rc_constant + dt)

    out = np.zeros_like(v)
    out[0] = v[0]
    for i in range(1, len(v)):
        out[i] = out[i - 1] + alpha * (v[i] - out[i - 1])
    return out


def avg_voltage(duty):
    return VCC * duty / 100.0


def pico_val(duty):
    """Maps 0-100% duty to Pico's 16-bit duty_u16() register (0-65535)."""
    return int(65535 * duty / 100.0)


def arduino_val(duty):
    """Maps 0-100% duty to Arduino's analogWrite() 8-bit value (0-255)."""
    return int(255 * duty / 100.0)


def period_us(freq):
    return 1_000_000.0 / freq


# ══════════════════════════════════════════════════════════════════════════
# LED COLOR HELPERS
# ══════════════════════════════════════════════════════════════════════════

def led_color_ch1(duty):
    """CH1 LED: warm pink → bright hot pink → white-pink at full."""
    b = duty / 100.0
    if b < 0.01:
        return "#150008", "#000000"
    r = min(1.0, 0.7 + 0.3 * b)
    g = b ** 1.8 * 0.35
    bl = b ** 1.2 * 0.55
    body = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(bl*255))
    glow = "#{:02x}{:02x}{:02x}".format(
        int(min(255, r*220)), int(min(255, g*180)), int(min(255, bl*200)))
    return body, glow


def led_color_ch2(duty):
    """CH2 LED: deep violet → purple → lavender-white at full."""
    b = duty / 100.0
    if b < 0.01:
        return "#080015", "#000000"
    r = b ** 1.5 * 0.65
    g = b ** 2.0 * 0.25
    bl = min(1.0, 0.5 + 0.5 * b)
    body = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(bl*255))
    glow = "#{:02x}{:02x}{:02x}".format(
        int(min(255, r*200)), int(min(255, g*180)), int(min(255, bl*220)))
    return body, glow


def brightness_label(duty):
    if duty < 1:    return "OFF"
    elif duty < 15: return "GLOW"
    elif duty < 35: return "DIM"
    elif duty < 60: return "MEDIUM"
    elif duty < 85: return "BRIGHT"
    else:           return "★ MAX ★"


# ══════════════════════════════════════════════════════════════════════════
# MATPLOTLIB GLOBAL STYLE
# ══════════════════════════════════════════════════════════════════════════

matplotlib.rcParams.update({
    "figure.facecolor":  BG,
    "axes.facecolor":    PANEL,
    "axes.edgecolor":    GRID,
    "axes.labelcolor":   DIM,
    "xtick.color":       DIMMER,
    "ytick.color":       DIMMER,
    "text.color":        TEXT,
    "grid.color":        GRID,
    "grid.linewidth":    0.6,
    "font.family":       "monospace",
})

# ══════════════════════════════════════════════════════════════════════════
# FIGURE LAYOUT
# ══════════════════════════════════════════════════════════════════════════

fig = plt.figure(figsize=(17, 10), facecolor=BG)
fig.canvas.manager.set_window_title(
    "PWMForge Elite v3 — Rose Quartz Edition | Day 17 BuildCored Orcas")

gs = gridspec.GridSpec(
    5, 3,
    figure=fig,
    height_ratios=[3.2, 3.2, 2.2, 0.6, 0.6],
    width_ratios=[5, 5, 3],
    hspace=0.55, wspace=0.38,
    left=0.05, right=0.98,
    top=0.91, bottom=0.06
)

# ── Header text ────────────────────────────────────────────────────────────
fig.text(0.5, 0.965,
         "PWMForge Elite  v3",
         ha="center", color=PINK, fontsize=22,
         fontweight="bold", family="monospace")

fig.text(0.5, 0.942,
         "Rose Quartz Edition  ·  Dual-Channel PWM + RC Filter  ·  BUILDCORED ORCAS — Day 17",
         ha="center", color=DIM, fontsize=8.5)

# thin decorative line under title
fig.add_artist(plt.Line2D([0.05, 0.95], [0.933, 0.933],
               transform=fig.transFigure, color=GRID, linewidth=1))

# ── CH1 Waveform  (row 0, col 0) ───────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
ax1.set_facecolor(PANEL)
ax1.set_title("Channel 1 — 1000 Hz  (LED / analogWrite)",
              color=PINK, fontsize=10, pad=5, loc="left")
ax1.set_ylabel("Voltage (V)", fontsize=8)
ax1.set_ylim(-0.35, VCC + 0.55)
ax1.grid(True, alpha=0.3)
ax1.tick_params(labelbottom=False)
for s in ax1.spines.values():
    s.set_color(GRID)

wave1_glow, = ax1.plot([], [], color=PINK_GLOW, lw=7, alpha=0.18, solid_capstyle="butt")
wave1,      = ax1.plot([], [], color=PINK,      lw=2.0, solid_capstyle="butt")
rc1_glow,   = ax1.plot([], [], color=RC_PINK,   lw=5, alpha=0.18, solid_capstyle="butt")
rc1_line,   = ax1.plot([], [], color=SOFT,      lw=1.6, linestyle="-", alpha=0.9)
avg1_line   = ax1.axhline(avg_voltage(CH1_DUTY_INIT),
                           color=AVG_PINK, lw=1.4, ls="--")
avg1_txt    = ax1.text(0.74, 0.22, "", transform=ax1.transAxes,
                        color=AVG_PINK, fontsize=8)
ax1.axhline(VCC, color=DIMMER, lw=0.6, ls=":")
ax1.text(0.99, 0.96, f"VCC {VCC}V", transform=ax1.transAxes,
         color=DIMMER, fontsize=7, ha="right")

legend1 = [
    Line2D([0],[0], color=PINK,   lw=2, label="PWM signal"),
    Line2D([0],[0], color=SOFT,   lw=1.6, label="RC filtered"),
    Line2D([0],[0], color=AVG_PINK, lw=1.4, ls="--", label="Average V"),
]
ax1.legend(handles=legend1, loc="upper right",
           facecolor=PANEL2, edgecolor=GRID, labelcolor=TEXT, fontsize=7)

# ── CH2 Waveform  (row 1, col 0) ───────────────────────────────────────────
ax2 = fig.add_subplot(gs[1, 0])
ax2.set_facecolor(PANEL)
ax2.set_title("Channel 2 — 300 Hz  (Servo / Motor control)",
              color=VIOLET, fontsize=10, pad=5, loc="left")
ax2.set_ylabel("Voltage (V)", fontsize=8)
ax2.set_xlabel("Time (ms)", fontsize=8)
ax2.set_ylim(-0.35, VCC + 0.55)
ax2.grid(True, alpha=0.3)
for s in ax2.spines.values():
    s.set_color(GRID)

wave2_glow, = ax2.plot([], [], color=VIOL_GLOW, lw=7, alpha=0.18, solid_capstyle="butt")
wave2,      = ax2.plot([], [], color=VIOLET,    lw=2.0, solid_capstyle="butt")
rc2_glow,   = ax2.plot([], [], color=RC_VIOL,   lw=5, alpha=0.18, solid_capstyle="butt")
rc2_line,   = ax2.plot([], [], color=VIOL_GLOW, lw=1.6, linestyle="-", alpha=0.9)
avg2_line   = ax2.axhline(avg_voltage(CH2_DUTY_INIT),
                           color=AVG_VIOL, lw=1.4, ls="--")
avg2_txt    = ax2.text(0.74, 0.22, "", transform=ax2.transAxes,
                        color=AVG_VIOL, fontsize=8)
ax2.axhline(VCC, color=DIMMER, lw=0.6, ls=":")
ax2.text(0.99, 0.96, f"VCC {VCC}V", transform=ax2.transAxes,
         color=DIMMER, fontsize=7, ha="right")

legend2 = [
    Line2D([0],[0], color=VIOLET,   lw=2, label="PWM signal"),
    Line2D([0],[0], color=VIOL_GLOW,lw=1.6, label="RC filtered"),
    Line2D([0],[0], color=AVG_VIOL, lw=1.4, ls="--", label="Average V"),
]
ax2.legend(handles=legend2, loc="upper right",
           facecolor=PANEL2, edgecolor=GRID, labelcolor=TEXT, fontsize=7)

# ── Phase Overlay  (row 0-1, col 1) ────────────────────────────────────────
ax_phase = fig.add_subplot(gs[0:2, 1])
ax_phase.set_facecolor(PANEL)
ax_phase.set_title("Phase Relationship — Both Channels Overlaid",
                   color=GOLD, fontsize=10, pad=5, loc="left")
ax_phase.set_xlabel("Time (ms)", fontsize=8)
ax_phase.set_ylabel("Voltage (V)", fontsize=8)
ax_phase.set_ylim(-0.35, VCC + 0.85)
ax_phase.grid(True, alpha=0.3)
for s in ax_phase.spines.values():
    s.set_color(GRID)

# Trigger line — oscilloscope style
trigger_line = ax_phase.axhline(VCC / 2, color=GOLD, lw=0.8,
                                 ls=":", alpha=0.7, label="Trigger (VCC/2)")
ph1_glow, = ax_phase.plot([], [], color=PINK_GLOW, lw=6, alpha=0.15, solid_capstyle="butt")
ph1,      = ax_phase.plot([], [], color=PINK,      lw=1.8, alpha=0.9, label="CH1", solid_capstyle="butt")
ph2_glow, = ax_phase.plot([], [], color=VIOL_GLOW, lw=6, alpha=0.15, solid_capstyle="butt")
ph2,      = ax_phase.plot([], [], color=VIOLET,    lw=1.8, alpha=0.9, label="CH2", solid_capstyle="butt")

ph_leg = [
    Line2D([0],[0], color=PINK,   lw=1.8, label="CH1 (1000 Hz)"),
    Line2D([0],[0], color=VIOLET, lw=1.8, label="CH2 (300 Hz)"),
    Line2D([0],[0], color=GOLD,   lw=0.8, ls=":", label="Trigger VCC/2"),
]
ax_phase.legend(handles=ph_leg, loc="upper right",
                facecolor=PANEL2, edgecolor=GRID, labelcolor=TEXT, fontsize=7)

# Phase annotation text
phase_note = ax_phase.text(0.01, 0.97,
    "← Both channels plotted on same time window\n"
    "   Notice: CH2 period is 3.3× longer than CH1",
    transform=ax_phase.transAxes,
    color=DIMMER, fontsize=7, va="top")

# ── LED panels  (row 0-1, col 2) ───────────────────────────────────────────
ax_led1 = fig.add_subplot(gs[0, 2])
ax_led1.set_facecolor(BG)
ax_led1.set_xlim(-2.2, 2.2)
ax_led1.set_ylim(-2.6, 2.3)
ax_led1.set_aspect("equal")
ax_led1.axis("off")
ax_led1.set_title("LED  CH1", color=PINK, fontsize=9, pad=2)

led1_halo  = Circle((0, 0), 1.7, color=PINK, alpha=0)
led1_body  = Circle((0, 0), 1.1, color="#150008")
led1_shine = Circle((0.38, 0.38), 0.28, color="#ffffff", alpha=0)
led1_base  = Rectangle((-0.45, -1.55), 0.9, 0.42, color="#2a1830", linewidth=0)
led1_p1    = Rectangle((-0.32, -2.15), 0.11, 0.62, color="#555", linewidth=0)
led1_p2    = Rectangle(( 0.21, -2.15), 0.11, 0.62, color="#555", linewidth=0)
led1_lbl   = ax_led1.text(0, -2.45, "OFF",
                           ha="center", color=DIM, fontsize=9, fontweight="bold")
led1_pct   = ax_led1.text(0, 0.05, f"{int(CH1_DUTY_INIT)}%",
                           ha="center", va="center", fontsize=16,
                           fontweight="bold", color=BG)
for p in [led1_halo, led1_body, led1_shine, led1_base, led1_p1, led1_p2]:
    ax_led1.add_patch(p)

ax_led2 = fig.add_subplot(gs[1, 2])
ax_led2.set_facecolor(BG)
ax_led2.set_xlim(-2.2, 2.2)
ax_led2.set_ylim(-2.6, 2.3)
ax_led2.set_aspect("equal")
ax_led2.axis("off")
ax_led2.set_title("LED  CH2", color=VIOLET, fontsize=9, pad=2)

led2_halo  = Circle((0, 0), 1.7, color=VIOLET, alpha=0)
led2_body  = Circle((0, 0), 1.1, color="#080015")
led2_shine = Circle((0.38, 0.38), 0.28, color="#ffffff", alpha=0)
led2_base  = Rectangle((-0.45, -1.55), 0.9, 0.42, color="#180828", linewidth=0)
led2_p1    = Rectangle((-0.32, -2.15), 0.11, 0.62, color="#555", linewidth=0)
led2_p2    = Rectangle(( 0.21, -2.15), 0.11, 0.62, color="#555", linewidth=0)
led2_lbl   = ax_led2.text(0, -2.45, "OFF",
                           ha="center", color=DIM, fontsize=9, fontweight="bold")
led2_pct   = ax_led2.text(0, 0.05, f"{int(CH2_DUTY_INIT)}%",
                           ha="center", va="center", fontsize=16,
                           fontweight="bold", color=BG)
for p in [led2_halo, led2_body, led2_shine, led2_base, led2_p1, led2_p2]:
    ax_led2.add_patch(p)

# ── Stats bar  (row 2, col 0-1) ────────────────────────────────────────────
ax_stats = fig.add_subplot(gs[2, 0:2])
ax_stats.set_facecolor(BG)
ax_stats.axis("off")
stats_txt = ax_stats.text(
    0.5, 0.5, "",
    transform=ax_stats.transAxes,
    ha="center", va="center",
    fontsize=8.2, color=TEXT, family="monospace",
    bbox=dict(boxstyle="round,pad=0.6",
              facecolor=PANEL, edgecolor=GRID, linewidth=1)
)

# ── Code export panel  (row 2, col 2) ──────────────────────────────────────
ax_code = fig.add_subplot(gs[2, 2])
ax_code.set_facecolor(BG)
ax_code.axis("off")
code_txt = ax_code.text(
    0.04, 0.97, "",
    transform=ax_code.transAxes,
    ha="left", va="top",
    fontsize=7, color=SOFT, family="monospace"
)

# ── Sliders  (rows 3-4) ────────────────────────────────────────────────────
# CH1 duty
sl_ax_d1 = plt.axes([0.06, 0.038, 0.38, 0.022], facecolor=PANEL)
sl_duty1 = Slider(sl_ax_d1, "CH1 Duty %", 0, 100,
                  valinit=CH1_DUTY_INIT, valstep=0.5, color=PINK)
sl_duty1.label.set_color(PINK); sl_duty1.valtext.set_color(PINK)

# CH2 duty
sl_ax_d2 = plt.axes([0.50, 0.038, 0.38, 0.022], facecolor=PANEL)
sl_duty2 = Slider(sl_ax_d2, "CH2 Duty %", 0, 100,
                  valinit=CH2_DUTY_INIT, valstep=0.5, color=VIOLET)
sl_duty2.label.set_color(VIOLET); sl_duty2.valtext.set_color(VIOLET)

# ── Buttons ────────────────────────────────────────────────────────────────
def mk_btn(rect, label):
    bax = plt.axes(rect, facecolor=PANEL)
    b = Button(bax, label, color=PANEL, hovercolor=PANEL2)
    b.label.set_color(TEXT); b.label.set_fontsize(8)
    return b

btn_sweep  = mk_btn([0.06,  0.008, 0.10, 0.026], "⟳ Sweep")
btn_reset  = mk_btn([0.18,  0.008, 0.10, 0.026], "↺ Reset")
btn_half   = mk_btn([0.30,  0.008, 0.10, 0.026], "50% Both")
btn_full   = mk_btn([0.42,  0.008, 0.10, 0.026], "100% Both")
btn_servo  = mk_btn([0.54,  0.008, 0.13, 0.026], "Servo Demo")
btn_fade   = mk_btn([0.69,  0.008, 0.13, 0.026], "Fade Demo")

fig.text(0.5, 0.001,
         "SPACE = sweep  |  R = reset  |  1 = 50% CH1  |  2 = 50% CH2",
         ha="center", fontsize=6.5, color=DIMMER)

# ══════════════════════════════════════════════════════════════════════════
# STATE
# ══════════════════════════════════════════════════════════════════════════
state = {
    "sweep":    False,
    "sweep_dir": 1,
    "fade":     False,
    "fade_dir": 1,
}

# ══════════════════════════════════════════════════════════════════════════
# LED UPDATER
# ══════════════════════════════════════════════════════════════════════════

def update_led(body, halo, shine, lbl, pct_txt, duty, color_fn):
    b = duty / 100.0
    col, gcol = color_fn(duty)
    body.set_color(col)
    halo.set_color(gcol)
    halo.set_alpha(b * 0.50)
    shine.set_alpha(b * 0.50)
    lbl.set_text(brightness_label(duty))
    lbl.set_color(PINK if duty > 70 else VIOLET if duty > 40 else DIM)
    pct_txt.set_text(f"{int(duty)}%")
    pct_txt.set_color(BG if b > 0.45 else TEXT)

# ══════════════════════════════════════════════════════════════════════════
# MAIN REFRESH
# ══════════════════════════════════════════════════════════════════════════

def refresh(_=None):
    d1 = sl_duty1.val
    d2 = sl_duty2.val

    # ── CH1 waveform ───────────────────────────────────────────────────
    t1, v1 = pwm_wave(d1, CH1_FREQ)
    filt1  = rc_filter(v1, CH1_FREQ)
    ax1.set_xlim(0, t1[-1])
    wave1_glow.set_data(t1, v1)
    wave1.set_data(t1, v1)
    rc1_glow.set_data(t1, filt1)
    rc1_line.set_data(t1, filt1)
    a1 = avg_voltage(d1)
    avg1_line.set_ydata([a1, a1])
    avg1_txt.set_text(f"avg = {a1:.3f} V  ({d1:.1f}%)")

    # ── CH2 waveform ───────────────────────────────────────────────────
    t2, v2 = pwm_wave(d2, CH2_FREQ)
    filt2  = rc_filter(v2, CH2_FREQ)
    ax2.set_xlim(0, t2[-1])
    wave2_glow.set_data(t2, v2)
    wave2.set_data(t2, v2)
    rc2_glow.set_data(t2, filt2)
    rc2_line.set_data(t2, filt2)
    a2 = avg_voltage(d2)
    avg2_line.set_ydata([a2, a2])
    avg2_txt.set_text(f"avg = {a2:.3f} V  ({d2:.1f}%)")

    # ── Phase overlay ──────────────────────────────────────────────────
    # Show both channels on a shared 15ms time window
    # This makes the frequency difference visually obvious
    t_shared = np.linspace(0, 15.0, SAMPLE_PTS)   # 15 ms window

    period1 = 1000.0 / CH1_FREQ   # ms
    period2 = 1000.0 / CH2_FREQ
    phase1 = (t_shared % period1) / period1
    phase2 = (t_shared % period2) / period2
    v_ph1 = np.where(phase1 < d1 / 100.0, VCC, 0.0)
    v_ph2 = np.where(phase2 < d2 / 100.0, VCC + 0.4, 0.4)  # offset CH2 slightly

    ph1_glow.set_data(t_shared, v_ph1)
    ph1.set_data(t_shared, v_ph1)
    ph2_glow.set_data(t_shared, v_ph2)
    ph2.set_data(t_shared, v_ph2)
    ax_phase.set_xlim(0, 15)

    # ── LEDs ───────────────────────────────────────────────────────────
    update_led(led1_body, led1_halo, led1_shine, led1_lbl, led1_pct,
               d1, led_color_ch1)
    update_led(led2_body, led2_halo, led2_shine, led2_lbl, led2_pct,
               d2, led_color_ch2)

    # ── Stats ──────────────────────────────────────────────────────────
    p1 = period_us(CH1_FREQ)
    h1 = p1 * d1 / 100.0
    l1 = p1 - h1

    p2 = period_us(CH2_FREQ)
    h2 = p2 * d2 / 100.0
    l2 = p2 - h2

    rc1_ripple = abs(VCC * d1/100 - filt1[-1])
    rc2_ripple = abs(VCC * d2/100 - filt2[-1])

    stats_txt.set_text(
        f"  CH1 │ {CH1_FREQ:.0f} Hz │ Duty: {d1:5.1f}% │ Period: {p1:7.1f} µs │"
        f" HIGH: {h1:7.1f} µs │ LOW: {l1:7.1f} µs │ Avg: {a1:.3f}V │"
        f" RC ripple: {rc1_ripple:.3f}V │ duty_u16: {pico_val(d1):5}  \n"
        f"  CH2 │ {CH2_FREQ:.0f} Hz │ Duty: {d2:5.1f}% │ Period: {p2:7.1f} µs │"
        f" HIGH: {h2:7.1f} µs │ LOW: {l2:7.1f} µs │ Avg: {a2:.3f}V │"
        f" RC ripple: {rc2_ripple:.3f}V │ duty_u16: {pico_val(d2):5}  "
    )

    # ── Code export ────────────────────────────────────────────────────
    code_txt.set_text(
        f"— Pico MicroPython —\n"
        f"from machine import Pin, PWM\n\n"
        f"ch1 = PWM(Pin(15))\n"
        f"ch1.freq({int(CH1_FREQ)})\n"
        f"ch1.duty_u16({pico_val(d1)})\n\n"
        f"ch2 = PWM(Pin(16))\n"
        f"ch2.freq({int(CH2_FREQ)})\n"
        f"ch2.duty_u16({pico_val(d2)})\n\n"
        f"— Arduino C++ —\n"
        f"analogWrite(9,  {arduino_val(d1):3});  // CH1\n"
        f"analogWrite(10, {arduino_val(d2):3});  // CH2"
    )

    fig.canvas.draw_idle()

# ══════════════════════════════════════════════════════════════════════════
# BUTTON CALLBACKS
# ══════════════════════════════════════════════════════════════════════════

def do_sweep(event=None):
    state["sweep"] = not state["sweep"]
    state["fade"] = False
    btn_sweep.label.set_text("■ Stop" if state["sweep"] else "⟳ Sweep")
    btn_fade.label.set_text("Fade Demo")
    fig.canvas.draw_idle()

def do_reset(event=None):
    state["sweep"] = False
    state["fade"] = False
    btn_sweep.label.set_text("⟳ Sweep")
    btn_fade.label.set_text("Fade Demo")
    sl_duty1.set_val(CH1_DUTY_INIT)
    sl_duty2.set_val(CH2_DUTY_INIT)

def do_half(event=None):
    sl_duty1.set_val(50); sl_duty2.set_val(50)

def do_full(event=None):
    sl_duty1.set_val(100); sl_duty2.set_val(100)

def do_servo(event=None):
    """
    Servo Demo: CH2 jumps to 7.5% duty — classic 1.5ms pulse on 300Hz.
    Real servos use 1-2ms pulse width for 0°-180° range.
    At 300 Hz period = 3333µs → 7.5% = ~250µs (scale for demo)
    """
    sl_duty2.set_val(7.5)
    sl_duty1.set_val(50)

def do_fade(event=None):
    state["fade"] = not state["fade"]
    state["sweep"] = False
    btn_fade.label.set_text("■ Stop" if state["fade"] else "Fade Demo")
    btn_sweep.label.set_text("⟳ Sweep")
    fig.canvas.draw_idle()

btn_sweep.on_clicked(do_sweep)
btn_reset.on_clicked(do_reset)
btn_half.on_clicked(do_half)
btn_full.on_clicked(do_full)
btn_servo.on_clicked(do_servo)
btn_fade.on_clicked(do_fade)

sl_duty1.on_changed(refresh)
sl_duty2.on_changed(refresh)

# ══════════════════════════════════════════════════════════════════════════
# KEYBOARD SHORTCUTS
# ══════════════════════════════════════════════════════════════════════════

def on_key(event):
    if event.key == " ":
        do_sweep()
    elif event.key in ("r", "R"):
        do_reset()
    elif event.key == "1":
        sl_duty1.set_val(50)
    elif event.key == "2":
        sl_duty2.set_val(50)

fig.canvas.mpl_connect("key_press_event", on_key)

# ══════════════════════════════════════════════════════════════════════════
# ANIMATION
# ══════════════════════════════════════════════════════════════════════════

def animate(frame):
    updated = False

    if state["sweep"]:
        # CH1 ramps up, CH2 ramps down — dramatic visual contrast
        d1 = sl_duty1.val + 0.9 * state["sweep_dir"]
        if d1 >= 100:
            d1 = 100; state["sweep_dir"] = -1
        elif d1 <= 0:
            d1 = 0; state["sweep_dir"] = 1
        d2 = 100 - d1
        sl_duty1.set_val(round(d1, 1))
        sl_duty2.set_val(round(d2, 1))
        updated = True

    if state["fade"]:
        # Both channels fade together — smooth breathing effect
        d1 = sl_duty1.val + 0.6 * state["fade_dir"]
        if d1 >= 100:
            d1 = 100; state["fade_dir"] = -1
        elif d1 <= 0:
            d1 = 0; state["fade_dir"] = 1
        sl_duty1.set_val(round(d1, 1))
        sl_duty2.set_val(round(d1, 1))
        updated = True

    if updated:
        refresh()
    return []

ani = animation.FuncAnimation(
    fig, animate, interval=38, blit=False, cache_frame_data=False
)

# ══════════════════════════════════════════════════════════════════════════
# INITIAL RENDER
# ══════════════════════════════════════════════════════════════════════════
refresh()

# ══════════════════════════════════════════════════════════════════════════
# LAUNCH
# ══════════════════════════════════════════════════════════════════════════
print()
print("╔═══════════════════════════════════════════════════════════════╗")
print("║     PWMForge Elite v3 — Rose Quartz Edition                  ║")
print("║     Dual-Channel PWM + RC Filter + Phase View                ║")
print("║     BuildCored Orcas — Day 17 / 30                           ║")
print("╠═══════════════════════════════════════════════════════════════╣")
print("║  CH1 → 1000 Hz  (LED dimming)                                ║")
print("║  CH2 →  300 Hz  (Servo / motor — different frequency!)        ║")
print("╠═══════════════════════════════════════════════════════════════╣")
print("║  CONTROLS                                                     ║")
print("║  Sliders  → change duty cycle per channel                    ║")
print("║  Sweep    → CH1↑ CH2↓ simultaneously                         ║")
print("║  Fade     → both channels breathe together                   ║")
print("║  Servo    → jump CH2 to servo position demo                  ║")
print("║  SPACE / R / 1 / 2  keyboard shortcuts                       ║")
print("╠═══════════════════════════════════════════════════════════════╣")
print("║  HARDWARE BRIDGE (copy code from the panel):                 ║")
print("║  duty_u16() value = exact Pico register. Zero translation.   ║")
print("╚═══════════════════════════════════════════════════════════════╝")
print()

plt.show()
print("\n✅ PWMForge Elite v3 — session ended. Ship it. 🐋")
