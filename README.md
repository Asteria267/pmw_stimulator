# ⬡ PWMSimulator Pro — Day 17 / BuildCored Orcas

> **Dual-Channel PWM Oscilloscope with Live LED Visualization, Code Export & Sweep Mode**

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python)
![matplotlib](https://img.shields.io/badge/matplotlib-3.x-orange?style=flat-square)
![numpy](https://img.shields.io/badge/numpy-1.x-013243?style=flat-square)
![Day](https://img.shields.io/badge/Day-17%20%2F%2030-00ff88?style=flat-square)
![Status](https://img.shields.io/badge/Status-Shipped-brightgreen?style=flat-square)

---

## 🎯 What This Is

A **portfolio-grade interactive PWM simulator** that visualizes Pulse Width Modulation — the technique every microcontroller uses to fake analog output from a purely digital pin. No DAC needed. Just timing.

Built for Day 17 of the BuildCored Orcas 30-day hardware challenge.

---

## 🔬 The Hardware Concept

```
PWM Waveform at 50% duty:
  3.3V ─┐   ┌───┐   ┌───┐
        │   │   │   │   │
  0.0V  └───┘   └───┘   └──
         ←──────────────→
         1 period (e.g. 1ms at 1kHz)

Average voltage = VCC × duty_fraction = 3.3 × 0.5 = 1.65V
```

The human eye (and most sensors) perceive the **average** voltage, not the switching. That's why:
- 100% duty → LED fully bright (3.3V average)
- 50% duty → LED half bright (1.65V average)
- 0% duty → LED off (0V average)

**Real-world uses:**
| Application | PWM Role |
|---|---|
| LED dimming | Duty cycle = perceived brightness |
| Servo motor | Pulse width = shaft angle (1–2ms) |
| DC motor speed | Duty cycle = average torque |
| Audio synthesis | High-freq PWM → filtered = analog audio |
| Switching power supplies | Duty cycle controls output voltage |

---

## ✨ Features

| Feature | Status |
|---|---|
| Channel A slider — duty cycle (0–100%) | ✅ |
| Channel B slider — duty cycle (0–100%) | ✅ |
| Channel A slider — frequency (100–5000 Hz) | ✅ |
| Channel B slider — frequency (different!) | ✅ |
| Live phosphor-glow oscilloscope waveform | ✅ |
| Average voltage dashed line (both channels) | ✅ |
| Virtual LED-A with warm color temperature | ✅ |
| Virtual LED-B with cool blue-white tones | ✅ |
| Sweep mode (auto-ramps duty A↑, B↓) | ✅ |
| Stats panel (period, HIGH/LOW µs, duty_u16) | ✅ |
| Pico MicroPython code export | ✅ |
| Arduino C++ code export | ✅ |
| Keyboard shortcuts (Space/R/P/A) | ✅ |
| Oscilloscope dark theme | ✅ |

---

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/buildcored-orcas.git
cd buildcored-orcas

# 2. Install dependencies
pip install matplotlib numpy

# 3. Run
python day17_pwm_simulator.py
```

**Linux — if tkinter is missing:**
```bash
sudo apt install python3-tk
```

---

## 🕹️ Controls

| Control | Action |
|---|---|
| CH-A Duty slider | Sets Channel A duty cycle (0–100%) |
| CH-A Freq slider | Sets Channel A frequency (100–5000 Hz) |
| CH-B Duty slider | Sets Channel B duty cycle |
| CH-B Freq slider | Sets Channel B frequency |
| `⟳ SWEEP` button | Auto-ramps duty cycles (A↑ B↓ simultaneously) |
| `↺ RESET` button | Returns all values to defaults |
| `🐍 Pico Code` | Shows MicroPython export in code panel |
| `⚡ Arduino` | Shows C++ analogWrite export |
| `50% Quick` | Sets both channels to 50% |
| `100% Full` | Sets both channels to 100% |
| `SPACE` | Toggle sweep |
| `R` | Reset |
| `P` | Pico code export |
| `A` | Arduino code export |

---

## 📡 TODO #1 — Second PWM Channel (Required)

**Implemented.** Channel B runs at **500 Hz** by default vs Channel A's **1000 Hz**.

This demonstrates a core real-hardware concept: microcontrollers have **multiple independent PWM channels** (the Pico has 16). Each channel has its own:
- Frequency register
- Duty cycle register
- Phase (can be synchronized or free-running)

On the Pico, each channel maps to a specific GPIO pin via PWM "slices":

```python
from machine import Pin, PWM

pwm_a = PWM(Pin(15))   # Slice 7A
pwm_a.freq(1000)
pwm_a.duty_u16(32768)  # 50%

pwm_b = PWM(Pin(16))   # Slice 0A — independent!
pwm_b.freq(500)        # Different frequency
pwm_b.duty_u16(16383)  # 25%
```

---

## 🔢 The Math

```
Average Voltage = VCC × (duty_cycle / 100)

Pico duty_u16 register = int(duty_fraction × 65535)
Arduino analogWrite    = int(duty_fraction × 255)

Example: 75% duty on 3.3V system
  V_avg         = 3.3 × 0.75 = 2.475V
  duty_u16      = int(0.75 × 65535) = 49151
  analogWrite   = int(0.75 × 255) = 191
```

---

## 🌉 v2.0 Bridge — Going Real Hardware

The code export panel generates **production-ready Pico code** you can run *today*:

```python
# Paste this into Thonny → Run on real Pico
from machine import Pin, PWM

led = PWM(Pin(15))
led.freq(1000)
led.duty_u16(32768)   # ← exact value from simulator stats panel
```

**The duty_u16 value displayed in the stats panel IS the hardware register value.** Zero translation needed between simulation and reality.

---

## 📁 Project Structure

```
buildcored-orcas/
├── day17_pwm_simulator.py   ← Main simulator (this file)
├── day17_starter.py         ← Original starter code
└── README.md
```

---

## 🧠 What I Learned

1. **PWM is fake analog** — digital pins can't output 1.65V, but they can average to it
2. **Duty cycle = average voltage** — mathematically: `V_avg = VCC × D`
3. **Frequency matters** — too low → visible flicker; too high → switching losses
4. **Multiple independent channels** — real hardware runs many PWMs simultaneously
5. **16-bit resolution on Pico** — `duty_u16(0–65535)` gives 65536 brightness levels vs Arduino's 256

---

## 🐋 BuildCored Orcas

Part of the **30-day hardware + embedded systems challenge**.

- Day 16 ← EchoKiller (Advanced)
- **Day 17 → PWMSimulator Pro** ← you are here
- Day 18 → coming up

---

*Shipped before midnight. 🐋*
