<div align="center">

# ✦ PWMForge Elite v3
## Rose Quartz Edition

**Dual-Channel PWM Oscilloscope · RC Filter · Phase Visualizer**

*BuildCored Orcas — Day 17 / 30*

---

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![matplotlib](https://img.shields.io/badge/matplotlib-3.x-ff4fa3?style=for-the-badge)
![numpy](https://img.shields.io/badge/numpy-1.x-b060ff?style=for-the-badge)
![Day](https://img.shields.io/badge/Day-17%20%2F%2030-ff4fa3?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-✓%20Shipped-ff4fa3?style=for-the-badge)

</div>

---

## 🌸 What Is This?

**PWMForge Elite** is an interactive desktop simulator that brings Pulse Width Modulation to life visually. If you've ever wondered *how a microcontroller dims an LED* or *how a servo knows what angle to go to* — this is the answer, running live on your screen.

It was built as **Day 17** of the BuildCored Orcas 30-day embedded systems challenge. No hardware needed. Just Python, a slider, and curiosity.

> **Beginner note:** You don't need to understand electronics to run this. Drag a slider and watch everything update in real time — the waveform, the average voltage, the virtual LED glowing brighter or dimmer. The physics explains itself.

---

## 🧠 Understanding PWM — From Zero

### The problem PWM solves

A microcontroller pin is **purely digital**. It has exactly two states:

| State | Voltage |
|---|---|
| HIGH (ON) | 3.3V (Pico) / 5V (Arduino) |
| LOW (OFF) | 0V |

There is no "1.65V" setting. No middle ground. Just on or off.

But what if you want a **dim** LED? Or a motor at **half speed**? Or a servo at **90 degrees**?

### The PWM trick

Instead of outputting a steady voltage, PWM **switches the pin ON and OFF very fast** — hundreds or thousands of times per second. So fast that:

- Your **eye can't see the flicker** — it perceives an average brightness
- A **motor** responds to the average force, not each individual pulse
- A **capacitor** charges to the average voltage (that's the RC filter)

```
100% duty (always ON):
  3.3V ████████████████████  → LED full bright

75% duty:
  3.3V ████████████░░░░████  → LED 75% bright

50% duty:
  3.3V ████████░░░░░░░░████  → LED half bright

25% duty:
  3.3V ████░░░░░░░░░░░░████  → LED dim

0% duty (always OFF):
  3.3V ░░░░░░░░░░░░░░░░░░░░  → LED off
```

### The formula

```
Average Voltage = VCC × (Duty Cycle / 100)

Examples at VCC = 3.3V:
  100% → 3.3 × 1.00 = 3.30V  (full on)
   75% → 3.3 × 0.75 = 2.47V
   50% → 3.3 × 0.50 = 1.65V  (half)
   25% → 3.3 × 0.25 = 0.82V
    0% → 3.3 × 0.00 = 0.00V  (off)
```

### Key terms explained simply

| Term | What it means |
|---|---|
| **Duty Cycle** | What % of each cycle the pin is HIGH. 50% = half the time ON. |
| **Frequency** | How many on/off cycles per second. 1000 Hz = 1000 cycles/sec. |
| **Period** | The length of one full cycle. Period = 1 / Frequency. At 1000 Hz, period = 1ms. |
| **Average Voltage** | What the LED/motor/servo "feels". VCC × duty fraction. |
| **VCC** | Supply voltage. 3.3V on Raspberry Pi Pico, 5V on Arduino Uno. |

---

## 🖥️ What You See On Screen

The simulator has **5 panels**, each teaching something different:

```
┌─────────────────────────┬──────────────────────────┬──────────┐
│  CH1 Waveform           │  Phase Overlay           │  LED-CH1 │
│  (1000 Hz, pink)        │  (both channels, 15ms)   │  🔴 pink │
├─────────────────────────┤                          ├──────────┤
│  CH2 Waveform           │                          │  LED-CH2 │
│  (300 Hz, violet)       │                          │  🟣 viol │
├─────────────────────────┴──────────────────────────┴──────────┤
│  Stats bar: period · HIGH/LOW time · avg V · RC ripple · code │
├────────────────────────────────────────────────────────────────┤
│  [Sliders]  [Sweep] [Reset] [50%] [100%] [Servo] [Fade]       │
└────────────────────────────────────────────────────────────────┘
```

**CH1 Waveform panel** — The pink square wave for Channel 1 (1000 Hz). The dashed line is the average voltage. The softer pink line behind the wave is the RC-filtered output — what you'd measure after a capacitor.

**CH2 Waveform panel** — Same thing for Channel 2 (300 Hz violet). Notice the pulses are wider because the frequency is lower — each period takes longer.

**Phase Overlay panel** — Both channels plotted on the same 15ms window. This is where the frequency difference becomes obvious: CH1 completes 3+ cycles while CH2 completes 1. This is exactly what a real dual-channel oscilloscope shows.

**LED panels** — Two virtual LEDs, one per channel. They glow brighter as duty increases. CH1's LED shifts from deep red-pink to bright hot pink. CH2's LED shifts from deep violet to bright lavender-white.

**Stats bar** — Live numbers: period in microseconds, HIGH/LOW time, average voltage, RC ripple voltage, and the exact `duty_u16()` value to paste into your Pico code.

---

## 🌊 The RC Filter — Bonus Hardware Concept

One of the features that makes this simulator stand out is the **RC filter overlay**.

### What is an RC filter?

A simple resistor (R) and capacitor (C) connected like this:

```
PWM pin ──[R]──┬──── output (smoother voltage)
               │
              [C]
               │
              GND
```

The capacitor charges when the pin is HIGH and discharges when it's LOW. If the PWM frequency is fast enough, the capacitor never fully discharges — and the output is a smooth (ish) analog voltage.

### Why does frequency matter?

This is the insight that separates beginners from people who *get it*:

- **CH1 at 1000 Hz** — the pin switches 1000 times per second. The capacitor barely has time to discharge. Output is smooth. **Low ripple.**
- **CH2 at 300 Hz** — the pin switches only 300 times per second. The capacitor has longer gaps to discharge. Output has more wobble. **Higher ripple.**

The **RC ripple voltage** in the stats bar shows this difference as a number. Try setting both channels to 50% duty and compare the ripple values — CH2 will always be higher.

> **Real world:** This is how microcontrollers output audio, generate reference voltages, and control LED brightness without a dedicated DAC chip. The Pico can do this on any of its PWM-capable GPIO pins.

---

## 📡 Dual Channel — The Core Requirement

This simulator runs **two completely independent PWM channels** at different frequencies, mirroring exactly how real microcontrollers work.

| | Channel 1 | Channel 2 |
|---|---|---|
| Frequency | 1000 Hz | 300 Hz |
| Typical use | LED dimming | Servo / motor |
| Colour | Hot pink 🌸 | Violet 🟣 |
| Pico GPIO | Pin 15 | Pin 16 |
| Period | 1000 µs | 3333 µs |

**Why different frequencies?**

Servos expect a pulse every ~20ms (50 Hz) or thereabouts. LEDs can be driven at 1kHz+ with no visible flicker. Motors fall somewhere in between. Real hardware runs multiple PWM channels simultaneously at completely different settings — that's what the two channels here demonstrate.

---

## 🔌 From Simulator to Real Hardware

The code panel on the right side of the simulator generates **production-ready MicroPython** that runs on a real Raspberry Pi Pico:

```python
from machine import Pin, PWM

# Channel 1 — LED on GPIO 15
ch1 = PWM(Pin(15))
ch1.freq(1000)
ch1.duty_u16(32767)   # ← this number updates live as you drag the slider

# Channel 2 — Servo on GPIO 16
ch2 = PWM(Pin(16))
ch2.freq(300)
ch2.duty_u16(16383)   # ← exact register value, no conversion needed
```

**The `duty_u16()` value in the stats bar is the exact number you paste into Thonny and run.** Zero translation between the simulator and real hardware. That's the whole point of the v2.0 bridge.

For Arduino:

```cpp
// analogWrite maps 0-100% to 0-255
analogWrite(9,  128);  // CH1 — 50% duty
analogWrite(10,  64);  // CH2 — 25% duty
```

---

## 🚀 Quick Start

### Step 1 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 2 — Run

```bash
python pwmforge_rose.py
```

### Step 3 — Play

Drag the sliders. Press Sweep. Watch the LEDs. Read the stats bar.

**If you get a tkinter error on Linux:**
```bash
sudo apt install python3-tk
python pwmforge_rose.py
```

**If you get a tkinter error on macOS:**
```bash
brew install python-tk
```

---

## 🎮 All Controls

### Sliders

| Slider | What it does |
|---|---|
| `CH1 Duty %` | Sets Channel 1's duty cycle from 0% (off) to 100% (full on) |
| `CH2 Duty %` | Sets Channel 2's duty cycle independently |

### Buttons

| Button | What happens |
|---|---|
| `⟳ Sweep` | CH1 slowly ramps from 0→100% while CH2 ramps 100→0%. Dramatic visual. |
| `Fade Demo` | Both channels breathe in sync — in together, out together. |
| `Servo Demo` | Snaps CH2 to 7.5% duty — demonstrates a servo centre-position pulse width. |
| `50% Both` | Sets both channels to 50% immediately. Good baseline to compare ripple. |
| `100% Both` | Both channels to full on. Both LEDs at max brightness. |
| `↺ Reset` | Returns everything to startup values. |

### Keyboard shortcuts

| Key | Action |
|---|---|
| `SPACE` | Toggle sweep on/off |
| `R` | Reset everything |
| `1` | Snap CH1 to 50% |
| `2` | Snap CH2 to 50% |

---

## 🎨 Customisation — Make It Yours

The entire visual identity lives in the **ROSE QUARTZ THEME** block near the top of `pwmforge_rose.py`. Every colour, glow, and accent is a single hex variable. Change any of them and the whole simulator updates.

### The colour variables

```python
# ══════════════════════════════════════════════════════
# ROSE QUARTZ THEME — edit these to customise everything
# ══════════════════════════════════════════════════════

BG        = "#0d0911"   # Main background (very dark purple-black)
PANEL     = "#17111d"   # Plot panel background
PANEL2    = "#1f1628"   # Slightly lighter panel (legend boxes)
GRID      = "#2b2033"   # Grid lines and borders
TEXT      = "#f7d9ea"   # Primary text (soft pink-white)
DIM       = "#9b7f92"   # Secondary text (muted mauve)
DIMMER    = "#4a3545"   # Tertiary text (very muted)

# Channel 1 — hot pink
PINK      = "#ff4fa3"   # Main waveform line colour
PINK_GLOW = "#ff8fc4"   # Glow layer behind the waveform
PINK_DIM  = "#3d0f24"   # Unused slot — great for fill areas

# Channel 2 — violet/lavender
VIOLET    = "#b060ff"   # Main waveform line colour
VIOL_GLOW = "#d0a0ff"   # Glow layer behind the waveform
VIOL_DIM  = "#1e0838"   # Unused slot

# Average voltage dashed lines
AVG_PINK  = "#ffd6e7"   # CH1 average line (light pink)
AVG_VIOL  = "#e0c0ff"   # CH2 average line (light violet)

# RC filter output lines
RC_PINK   = "#ff9fcc"   # CH1 filtered output
RC_VIOL   = "#c890ff"   # CH2 filtered output

# Accents
GOLD      = "#ffd700"   # Trigger line + phase panel title
SOFT      = "#ffc1dd"   # RC line on CH1 waveform
```

### Recipes — copy and paste these

**🌊 Ocean Neon** — cyan and electric blue on near-black:
```python
BG        = "#020b12"
PANEL     = "#071520"
GRID      = "#0d2a3a"
PINK      = "#00f5d4"
PINK_GLOW = "#80ffee"
VIOLET    = "#0096ff"
VIOL_GLOW = "#70c8ff"
AVG_PINK  = "#aaffee"
AVG_VIOL  = "#aadcff"
RC_PINK   = "#00d4b8"
RC_VIOL   = "#0077cc"
GOLD      = "#ffdd00"
TEXT      = "#d0f8f0"
DIM       = "#5a9a8a"
DIMMER    = "#1a4a40"
```

**🌿 Matrix Green** — classic phosphor green terminal look:
```python
BG        = "#020902"
PANEL     = "#061206"
GRID      = "#0f2a0f"
PINK      = "#00ff44"
PINK_GLOW = "#80ff99"
VIOLET    = "#00cc33"
VIOL_GLOW = "#66ff88"
AVG_PINK  = "#aaffbb"
AVG_VIOL  = "#88ff99"
RC_PINK   = "#00ee55"
RC_VIOL   = "#00aa33"
GOLD      = "#ffff00"
TEXT      = "#ccffcc"
DIM       = "#4a8a4a"
DIMMER    = "#1a3a1a"
```

**🔥 Lava** — fire orange and amber on charcoal:
```python
BG        = "#100800"
PANEL     = "#1a0e00"
GRID      = "#2a1a00"
PINK      = "#ff6600"
PINK_GLOW = "#ffaa44"
VIOLET    = "#ff3300"
VIOL_GLOW = "#ff8866"
AVG_PINK  = "#ffcc88"
AVG_VIOL  = "#ffaa66"
RC_PINK   = "#ff8833"
RC_VIOL   = "#ff5500"
GOLD      = "#ffff44"
TEXT      = "#ffe8cc"
DIM       = "#aa7744"
DIMMER    = "#442200"
```

**🌸 Soft Sakura** — lighter, pastel take on the Rose Quartz theme:
```python
BG        = "#1a0f1a"
PANEL     = "#22102a"
GRID      = "#3a1f3a"
PINK      = "#ff80c0"
PINK_GLOW = "#ffb0d8"
VIOLET    = "#cc88ff"
VIOL_GLOW = "#ddbbff"
AVG_PINK  = "#ffddee"
AVG_VIOL  = "#eeddff"
RC_PINK   = "#ff99cc"
RC_VIOL   = "#cc99ff"
GOLD      = "#ffe066"
TEXT      = "#ffe8f5"
DIM       = "#bb88aa"
DIMMER    = "#553355"
```

### Tweaking the glow intensity

The glow effect is a thick, transparent line drawn behind the main waveform. Two variables control it:

```python
# In the plot setup — find these lines and adjust alpha:
wave1_glow, = ax1.plot([], [], color=PINK_GLOW, lw=7, alpha=0.18, ...)
#                                               ^^^        ^^^^
#                                          line width    transparency
#                                          (thicker = bigger glow)
#                                                    (higher = brighter glow)
```

- `lw=7, alpha=0.18` — current default (subtle, elegant)
- `lw=12, alpha=0.30` — stronger bloom, more cyberpunk
- `lw=4, alpha=0.10` — minimal, clean
- `lw=15, alpha=0.40` — extreme glow, very dramatic in sweep mode

### Tweaking the LED glow radius

The LED halo is a `Circle` patch. Find this section and change the radius:

```python
led1_halo = Circle((0, 0), 1.7, ...)   # 1.7 = current radius
#                           ^^^
#                    increase for bigger glow area
#                    1.2 = tight glow
#                    2.2 = wide atmospheric halo
```

And the max alpha in the `update_led()` function:

```python
halo.set_alpha(b * 0.50)
#                  ^^^^
#              0.30 = subtle  |  0.70 = intense  |  0.90 = full bloom
```

---

## 📊 Reading the Stats Bar

The stats bar at the bottom gives you the same data a real oscilloscope would show:

```
CH1 │ 1000 Hz │ Duty: 50.0% │ Period: 1000.0 µs │ HIGH: 500.0 µs │ LOW: 500.0 µs │ Avg: 1.650V │ RC ripple: 0.012V │ duty_u16: 32767
CH2 │  300 Hz │ Duty: 25.0% │ Period: 3333.3 µs │ HIGH: 833.3 µs │ LOW: 2500.0 µs │ Avg: 0.825V │ RC ripple: 0.089V │ duty_u16: 16383
```

| Column | What it means |
|---|---|
| Freq | How many cycles per second |
| Duty | What % of each cycle the pin is HIGH |
| Period | Duration of one complete cycle in microseconds (µs) |
| HIGH | How long the pin stays at 3.3V per cycle |
| LOW | How long the pin stays at 0V per cycle |
| Avg | Average voltage = what the LED/motor actually receives |
| RC ripple | How much the filtered output wobbles above/below the average |
| duty_u16 | The exact number to pass into `pwm.duty_u16()` on a Pico |

> **Notice:** CH2's RC ripple is always higher than CH1's at the same duty cycle. Lower frequency = more ripple. This is fundamental low-pass filter behaviour.

---

## 🔧 Project Structure

```
buildcored-orcas/
│
├── pwmforge_rose.py      ← The simulator (run this)
├── requirements.txt      ← pip install -r requirements.txt
└── README.md             ← You are here
```

### Inside pwmforge_rose.py

The file is organised into clear sections:

| Section | What's in it |
|---|---|
| Theme constants | All colour hex codes — edit here to customise |
| Signal engine | `pwm_wave()`, `rc_filter()`, `avg_voltage()` — the physics |
| LED colour helpers | `led_color_ch1()`, `led_color_ch2()` — brightness → RGB |
| Figure layout | All matplotlib axes, sliders, buttons created here |
| `refresh()` | The main update function — called every time a slider moves |
| Button callbacks | `do_sweep()`, `do_reset()`, `do_fade()`, `do_servo()` |
| Animation loop | `animate()` — drives sweep and fade modes at 38ms intervals |

---

## 💡 What I Learned Building This

1. **PWM is fake analog** — a digital pin can't output 1.65V, but it can *average* to it
2. **Duty cycle = average voltage** — the formula `V = VCC × D` is all you need
3. **Frequency matters for filtering** — higher frequency → smoother RC output → less ripple
4. **Multiple independent channels** — the Pico has 16 PWM channels; each has its own freq and duty
5. **16-bit resolution on Pico** — `duty_u16(0–65535)` gives 65,536 brightness steps vs Arduino's 256
6. **RC filters are free DACs** — no extra chip needed; just a resistor and capacitor

---

## 🌉 v2.0 Hardware Bridge

Everything in this simulator maps directly to real Pico hardware. The `duty_u16()` value updates live as you drag sliders. When you move to v2.0 hardware:

```python
# This runs on a real Raspberry Pi Pico — copy from the code panel
from machine import Pin, PWM

ch1 = PWM(Pin(15))
ch1.freq(1000)
ch1.duty_u16(32767)   # ← read this number off the stats bar

ch2 = PWM(Pin(16))
ch2.freq(300)
ch2.duty_u16(16383)   # ← same
```

**No conversion. No lookup tables. The simulator IS the hardware model.**

---

<div align="center">

*Rose Quartz Edition · Shipped before midnight · BuildCored Orcas Day 17*

🐋

</div>
