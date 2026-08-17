# ANAM-VII — Second-Stage Avionics

Flight avionics for the second stage of **ANAM-VII**, a two-stage sounding rocket built by
**GOROCKET**, the Korea University rocketry team, for the NURA national collegiate rocketry
competition.

The board handles altitude sensing, launch detection, second-stage ignition, parachute and
CanSat deployment, onboard data logging, and telemetry downlink.

Two revisions flew during the 2026 test campaign. **Revision 1 suffered a premature
second-stage ignition on the launch pad.** Revision 2, built around the root-cause analysis of
that failure, flew successfully. This repository documents both, including what went wrong and
why the fix was designed the way it was.

**Role:** second-stage avionics lead — schematic capture, PCB layout, bring-up, failure
analysis, and the Rev 2 redesign.

---

## System overview

| | Revision 1 (June 2026) | Revision 2 (July 2026) |
|---|---|---|
| MCU | Raspberry Pi Pico (RP2040) | Raspberry Pi Pico (RP2040) |
| Firmware | MicroPython | MicroPython |
| Barometer | BMP280 | **BMP581** |
| IMU / accelerometer | WT901 | **WT61** |
| Telemetry radio | E32-433T20D (LoRa, 433 MHz) | E32-433T20D (LoRa, 433 MHz) |
| Storage | microSD module (SPI) | microSD module (SPI) |
| Actuators | 3 × MG996R servo | 3 × MG996R servo |
| Ignition switching | AO3400 MOSFET + SLA-5VDC-SL-A relay | AO3400 MOSFET + **HR702-NH-DC5V relay** |
| Isolation | **none** | **4 × 6N137 optocoupler** |
| Umbilical sense | GPIO, no external pull-up | **GPIO with external pull-up to 3V3** |
| Umbilical connector | 2.54 mm pin header | **HT3.96 screw terminal** |
| Board | 2-layer, 80 × 100 mm | 2-layer, 80 × 100 mm |
| Reverse-polarity protection | 2 × AO3401 P-MOSFET | removed (see below) |
| Outcome | premature pad ignition; parachute did not deploy | **nominal flight** |


Power is split into two switched rails — a 3.7 V LiPo rail (VCC1) and a 5 V rail (VCC2) — each
with its own arming switch, so avionics logic and high-current actuator loads can be brought up
independently.

### Functional chain

```
BMP581 (I²C) ─┐
              ├─→ RP2040 ──→ launch decision ──→ 6N137 ──→ AO3400 ──→ relay ──→ igniter
WT61 (UART) ──┤        │
              │        ├──→ 6N137 ──→ servo 1  (parachute: nose cone splits laterally)
umbilical ────┘        ├──→ 6N137 ──→ servo 2  ┐ CanSat rotary door
                       ├──→ 6N137 ──→ servo 3  ┘
                       ├──→ microSD  (flight log)
                       └──→ E32 LoRa (telemetry downlink)
```

---

## Revision 1 — pad anomaly

### What happened

During launch-pad installation, the second-stage avionics concluded that launch had occurred
while the vehicle was still on the pad. The second stage ignited on the rail.

Two independent failures occurred on this flight:

1. **Electrical — false launch detection.** The safety-pin umbilical stopped conducting during
   pad setup. The launcher-tie umbilical remained connected and behaved normally. Because
   launch detection relied on the umbilical line alone, loss of that single signal was
   sufficient to trigger the full flight sequence.
2. **Mechanical — parachute failed to deploy.** The nose cone opened correctly and the
   parachute was exposed to the airstream, but the shroud lines were tangled and the canopy
   never inflated. The CanSat ejected normally and its parachute deployed as designed.

The two failures are unrelated and were addressed separately.

### Root cause of the false launch detection

Three design decisions combined:

**1. Single-signal launch detection.** Firmware treated umbilical disconnection as sufficient
evidence of launch. There was no requirement for agreement from any independent sensor, and no
persistence or debounce requirement on the signal.

**2. High-impedance umbilical sense node.** The umbilical connectors were wired pin 1 to GND,
pin 2 to a GPIO, with no external pull-up. When the umbilical is detached the node is left
floating and held only by the RP2040's internal pull-up, which is weak (tens of kΩ). Umbilical
runs are long and effectively act as antennas, and they sit alongside servo and relay switching
transients. An intermittent contact or induced noise on that node is indistinguishable from a
genuine detach event.

**3. Connector choice.** The umbilicals broke out to bare 2.54 mm male pin headers. A 0.1 in
header mated with a friction-fit socket has no positive latch and low retention force, and its
contact resistance degrades with repeated mating and handling — a poor choice for an interface
whose entire purpose is to be pulled apart reliably, and to stay connected until it is.

Note that the ignition path itself was **not** unguarded. Rev 1 already required two conditions
in series — an external arming switch feeding the relay coil high side, and the MCU asserting
the ignition GPIO into the coil low-side MOSFET — so software alone could not fire the igniter.
The failure was that once firmware wrongly concluded "launched," the only remaining barrier was
procedural: the arming switch had already been closed as part of pad setup.

### Also found in Rev 1

Schematic review after the flight showed `SERVO2` routed to **pin 30 (RUN)** of the Pico, which
is the reset input rather than a GPIO. This was worked around on the physical board with a
patch wire during assembly. It is corrected properly in Rev 2.

---

## Revision 2 — changes and rationale

### Launch detection

Altitude is now part of the launch decision: the flight sequence requires the umbilical
indication **and** a barometric altitude gain above ~10 m. A stuck or noisy umbilical line can
no longer arm the sequence on its own. The barometer was upgraded from BMP280 to **BMP581** for
the lower noise floor and finer resolution this threshold demands.

### Umbilical sense hardening

- **4.7 kΩ pull-up resistors to 3V3** added on both umbilical sense lines, replacing reliance on
  the RP2040 internal pull-up. At roughly 0.7 mA the sense node is now held at a defined logic
  level with an order of magnitude lower source impedance, making it far less susceptible to
  induced noise.
- **Connectors changed from 2.54 mm pin headers to HT3.96 screw terminals** on both umbilicals,
  after the header contacts were judged to be the physical failure point. A screwed conductor
  cannot back out under handling, and the mating force now comes from the umbilical lanyard
  rather than from a friction fit.

### Galvanic isolation

All four MCU control lines that drive high-current loads now pass through **6N137 high-speed
optocouplers** — one per servo channel and one on the ignition line:

- Input side: 271 Ω series resistor from the 3.3 V GPIO (≈12 mA LED drive)
- Output side: 1 kΩ pull-up to the 5 V actuator rail

The **grounds of the servo and ignition domains are separated from the MCU ground.** Servo
stall currents and igniter firing current no longer share a return path with the logic ground,
so switching transients on those loads cannot disturb the MCU's ground reference. Rev 1 had no
isolation of any kind.

### Ignition switching

The relay was changed to the physically smaller **HR702-NH-DC5V**. The two-condition interlock
is retained — external arming switch on the coil high side, MOSFET on the low side, with the
gate held off by a 10 kΩ pull-down and driven through a 100 Ω series resistor, and a 1N4007
flyback diode across the coil.

### Reverse-polarity protection removed

Rev 1 carried two AO3401 P-MOSFETs for reverse-polarity protection, one on each battery input
(3.7 V and 5 V). These were dropped in Rev 2: the JST VH battery connectors are mechanically
keyed and cannot be mated backwards, making the MOSFETs redundant against the failure they
guarded. The parts were also
out of stock at build time, and the team judged a re-order unwarranted.

The residual risk is a battery harness crimped with reversed polarity, which connector keying
does not catch. That is handled as an assembly-checklist item rather than in hardware.

### Pin assignment and schematic hygiene

- `SERVO2` moved off **pin 30 (RUN)** to **GP22**, eliminating the Rev 1 patch wire.
- All unused pins explicitly marked no-connect.

### Layout

On Rev 1 the connector footprints were spaced too tightly. Parts intended for the top layer did
not fit and had to be alternated between top and bottom during assembly, which made the board
awkward to build and to service. Rev 2 increased inter-component clearance and reworked
placement so connectors sit on accessible edges, with the ground pours split to match the
isolated-domain topology.

### Result

Rev 2 flew nominally in the second test launch, July 2026.

---

## Repository contents

```
hardware/
  rev1/                  schematic and PCB (June 2026 flight configuration)
  rev2/                  schematic and PCB (July 2026 flight configuration)
firmware/                MicroPython flight software
docs/
  failure-analysis.md    Rev 1 pad anomaly write-up
  images/                board photos, layout renders, flight data plots
```

Designed in **EasyEDA**.

---

## Notes

This is student competition hardware, not a qualified flight system. The Rev 2 interlock and
launch-detection changes were reviewed within the team before flight; anyone reusing this design
should treat the ignition and arming sections as a starting point for their own safety review,
not as a validated reference.

Rev 1 and Rev 2 were team efforts. This repository documents the second-stage avionics
subsystem, which was my responsibility; propulsion, structures, and recovery hardware were owned
by other sections of GOROCKET.
