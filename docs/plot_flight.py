"""
ANAM-VII second-stage flight data — 31 July 2026
Reads the onboard SD log and plots altitude, acceleration, tilt and state.
"""
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = "0731_stage2.xlsx"

df = pd.read_excel(SRC)
df["t"] = (df.t_ms - df.t_ms.iloc[0]) / 1000.0
df["amag"] = np.sqrt(df.ax**2 + df.ay**2 + df.az**2)

MODE = {1: "1: one umbilical released",
        2: "2: launch confirmed, awaiting 2nd-stage ignition",
        3: "3: post-ignition, awaiting recovery",
        4: "4: parachute out, descending"}
ev = {}
for c in ["ignited", "para", "cansat"]:
    hit = df.index[df[c].diff() == 1]
    if len(hit):
        ev[c] = df.t[hit[0]]

apogee_t = df.t[df.alt_m.idxmax()]
apogee_a = df.alt_m.max()

fig, ax = plt.subplots(3, 1, figsize=(9, 9), sharex=True,
                       gridspec_kw={"height_ratios": [3, 2, 2]})

# mode bands
colors = {1: "#eceff1", 2: "#ffe0b2", 3: "#c8e6c9", 4: "#bbdefb"}
prev, start = df["mode"].iloc[0], df.t.iloc[0]
for i in range(1, len(df)):
    if df["mode"].iloc[i] != prev:
        for a in ax:
            a.axvspan(start, df.t.iloc[i], color=colors.get(prev, "#fff"), zorder=0)
        prev, start = df["mode"].iloc[i], df.t.iloc[i]
for a in ax:
    a.axvspan(start, df.t.iloc[-1], color=colors.get(prev, "#fff"), zorder=0)

ax[0].plot(df.t, df.alt_m, color="#1f3864", lw=1.8, zorder=3)
ax[0].plot(apogee_t, apogee_a, "o", color="#c62828", ms=7, zorder=4)
ax[0].annotate(f"apogee {apogee_a:.1f} m", (apogee_t, apogee_a),
               textcoords="offset points", xytext=(8, 6), fontsize=9, color="#c62828")
ax[0].axhline(10, color="#888", ls=":", lw=1)
LAUNCH_T0 = 0.674
ax[0].axvline(LAUNCH_T0, color="#1565c0", ls="-.", lw=1.2, zorder=2)
ax[0].text(LAUNCH_T0, ax[0].get_ylim()[1]*0.55, " liftoff\n 0.67s", fontsize=8, color="#1565c0")
ax[0].text(df.t.iloc[-1], 11.5, "10 m", ha="right",
           fontsize=8, color="#555")
ax[0].set_ylabel("Altitude (m)")
ax[0].set_title("ANAM-VII second stage — 31 July 2026", fontsize=12, weight="bold")

ax[1].plot(df.t, df.amag, color="#2e7d32", lw=1.4)
ax[1].set_ylabel("|acceleration| (g)")

ax[2].plot(df.t, df.tilt_deg, color="#6a1b9a", lw=1.4)
ax[2].set_ylabel("Tilt (deg)")
ax[2].set_xlabel("Time since log start (s)")

labels = {"ignited": "2nd-stage ignition cmd", "para": "parachute (tilt abort)", "cansat": "CanSat release"}
for k, t in ev.items():
    for a in ax:
        a.axvline(t, color="#c62828", ls="--", lw=1.2, zorder=2)
    ax[0].text(t, ax[0].get_ylim()[1]*0.97, f" {labels[k]}\n {t:.2f}s",
               rotation=90, va="top", fontsize=8, color="#c62828")

handles = [plt.Rectangle((0,0),1,1, color=colors[m]) for m in sorted(MODE)]
ax[0].legend(handles, [MODE[m] for m in sorted(MODE)],
             loc="lower left", fontsize=7.5, framealpha=.92)

for a in ax:
    a.grid(alpha=.25, zorder=1)
plt.tight_layout()
plt.savefig("flight/flight-profile.png", dpi=160)
print("apogee %.2f m at %.2f s" % (apogee_a, apogee_t))
print("events:", {k: round(v,3) for k,v in ev.items()})
