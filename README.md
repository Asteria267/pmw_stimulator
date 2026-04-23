# ⬡ PWMForge Elite v3 — Rose Quartz Edition
### Dual-Channel PWM + RC Filter + Phase View | BuildCored Orcas Day 17

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python)
![matplotlib](https://img.shields.io/badge/matplotlib-3.x-ff4fa3?style=flat-square)
![numpy](https://img.shields.io/badge/numpy-1.x-b060ff?style=flat-square)
![Day](https://img.shields.io/badge/Day-17%20%2F%2030-ff4fa3?style=flat-square)
![Status](https://img.shields.io/badge/Status-Shipped-ff4fa3?style=flat-square)

---

## What Is This?

A **dual-channel PWM oscilloscope simulator** that visualises Pulse Width Modulation — the technique every microcontroller uses to fake analog output from a purely digital pin. No DAC required. Just timing.

---

## The Hardware Concept

```
PWM at 50% duty, 1000 Hz:

3.3V ─┐   ┌───┐   ┌───┐   ┌───
      │   │   │   │   │   │
0.0V  └───┘   └───┘   └───┘

     |← 1ms period →|

Average = 3.3 × 0.50 = 1.65V
```

The LED (or motor, or servo) only "sees" the **average voltage** — not the switching. That's the magic of PWM.

---

## Features

| Feature | Status |
|---|---|
| Channel 1 — 1000 Hz PWM with duty slider | ✅ |
| Channel 2 — 300 Hz PWM (different freq — TODO #1) | ✅ |
| Live square-wave with phosphor glow effect | ✅ |
| RC filter output overlaid on each channel | ✅ |
| Average voltage dashed line (both channels) | ✅ |
| Phase relationship overlay (15ms shared window) | ✅ |
| Oscilloscope trigger line (VCC/2) | ✅ |
| Virtual LED per channel (pink / violet) | ✅ |
| RC ripple voltage in stats | ✅ |
| Sweep mode (CH1↑ CH2↓) | ✅ |
| Fade mode (both breathe together) | ✅ |
| Servo demo button | ✅ |
| Live Pico MicroPython + Arduino C++ code export | ✅ |
| Keyboard shortcuts (SPACE / R / 1 / 2) | ✅ |
| Rose Quartz oscilloscope dark theme | ✅ |

---

## Quick Start

```bash
pip install -r requirements.txt
python pwmforge_rose.py
```

**Linux — if tkinter is missing:**
```bash
sudo apt install python3-tk
```

---

## Controls

| Control | Action |
|---|---|
| CH1 Duty slider | Channel 1 duty cycle (0–100%) |
| CH2 Duty slider | Channel 2 duty cycle (0–100%) |
| `⟳ Sweep` | CH1 ramps up while CH2 ramps down |
| `Fade Demo` | Both channels breathe in sync |
| `Servo Demo` | CH2 jumps to 7.5% (servo centre position demo) |
| `50% Both` | Both channels to 50% |
| `100% Both` | Both channels to full |
| `↺ Reset` | Back to defaults |
| `SPACE` | Toggle sweep |
| `R` | Reset |
| `1` / `2` | Quick 50% on CH1 / CH2 |

---

## The RC Filter — Bonus Hardware Concept

A resistor + capacitor smooths the PWM square wave into a real analog voltage. This simulator shows the difference live:

- **CH1 at 1000 Hz** → faster switching → capacitor stays more charged → smoother RC output
- **CH2 at 300 Hz** → slower switching → longer gaps → capacitor discharges more → visible ripple

The **RC ripple voltage** in the stats bar quantifies this numerically.

```
PWM pin → [R] → ──┬── analog-ish output
                  │
                 [C]
                  │
                 GND
```

This is how cheap audio DACs work on microcontrollers — no dedicated chip needed.

---

## Dual Channel — Required TODO #1

CH1 runs at **1000 Hz**, CH2 at **300 Hz**. The phase overlay panel makes this difference obvious — you can count 3+ CH1 cycles for every single CH2 cycle.

Live Pico code in the side panel:

```python
from machine import Pin, PWM

ch1 = PWM(Pin(15))
ch1.freq(1000)
ch1.duty_u16(32767)   # ← exact value from stats bar

ch2 = PWM(Pin(16))
ch2.freq(300)
ch2.duty_u16(16383)
```

The `duty_u16()` value shown is the **exact hardware register** — zero translation between simulator and real Pico.

---

## Project Structure

```
buildcored-orcas/
├── pwmforge_rose.py     ← Main simulator
├── requirements.txt
└── README.md
```

---

*Rose Quartz Edition. Shipped before midnight. 🐋*
