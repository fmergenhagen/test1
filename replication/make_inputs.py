"""
Build 15-minute input profiles (one week, T = 672) for the swarm-grid replication of
Ouanes et al. (2026), Energy Economics 163, 109598.

The paper uses RAMP v0.5.1 load profiles and a PVGIS TMY solar profile for
Ambohimena (northern Madagascar). Neither input file is published with the
article, so the profiles here are SYNTHETIC STAND-INS calibrated to:
  * the shapes in the paper's Fig. 3 (solar) and Fig. 4 (loads), and
  * the weekly energy totals implied by Table 6, scenario 4a
    (revenue at the fixed 2 EUR/kWh tariff = profit + cost):
        households  (86.01 + 0.40) / 2 = 43.2 kWh/week
        streetlights (57.21 + 1.22) / 2 = 29.2 kWh/week
        school      (37.65 + 5.44) / 2 = 21.5 kWh/week

To use real data instead, overwrite data/profiles.csv with columns
    t, solar_cf, hh_a, hh_b, hh_c, streetlights, school
(kWh per kWp and step for solar_cf, kWh per step for the loads).
"""
import numpy as np
import pandas as pd

SPH, DAYS = 4, 7                     # steps per hour; the paper's tables use 15-min data
T = 24 * SPH * DAYS
DT = 1 / SPH                         # hours per step
clock = (np.arange(T) % (24 * SPH)) / SPH    # time of day in hours (0, 0.25, ...)
hours = clock.astype(int)
day = np.arange(T) // (24 * SPH)

# ---------------------------------------------------------------- solar (Fig. 3)
# Bell between ~06:00 and ~18:00, peak 0.60-0.72 kW/kWp depending on the day.
rng = np.random.default_rng(2026)
x = np.clip((clock + DT / 2 - 6.0) / 12.0, 0, 1)
bell = np.sin(np.pi * x) ** 1.6
daily_peak = np.array([0.66, 0.72, 0.62, 0.70, 0.71, 0.58, 0.69])
solar = bell * daily_peak[day]
solar *= 1 + 0.05 * rng.standard_normal(T) * (solar > 0.05)      # light cloud noise
solar = np.clip(solar, 0, None)


# ---------------------------------------------------------------- loads (Fig. 4)
def household_group(seed, weekly_kwh):
    """Five households: flat-ish base, morning bump, evening peak, noisy."""
    r = np.random.default_rng(seed)
    base = np.full(24, 0.20)
    base[6:9] += 0.05
    base[9:17] += 0.07
    base[17:22] += 0.16
    base[22:] -= 0.04
    base[:5] -= 0.05
    prof = base[hours] * (1 + 0.22 * r.standard_normal(T))
    prof *= 1 + 0.06 * r.standard_normal(DAYS)[day]              # day-to-day level
    prof = np.clip(prof, 0.05, None)
    return prof * weekly_kwh / prof.sum()


def streetlights(weekly_kwh):
    """Ten lamps, 0.4 kW in total, on from ~19:00 to ~05:30."""
    prof = np.where((hours >= 19) | (hours <= 4), 0.4, 0.0).astype(float)
    prof[(clock >= 5) & (clock < 5.5)] = 0.4
    return prof * weekly_kwh / prof.sum()


def school(seed, weekly_kwh):
    """Low standby, spiky daytime use on weekdays, little on the weekend."""
    r = np.random.default_rng(seed)
    prof = np.full(T, 0.07) * (1 + 0.25 * r.standard_normal(T))
    weekday = day < 5
    open_hours = (hours >= 8) & (hours <= 16)
    bump = np.where(open_hours, 0.16 + 0.20 * r.random(T), 0.0)
    spikes = np.where(open_hours & (r.random(T) < 0.30), 0.25 * r.random(T), 0.0)
    prof += np.where(weekday, bump + spikes, 0.25 * bump)
    prof = np.clip(prof, 0.02, None)
    return prof * weekly_kwh / prof.sum()


df = pd.DataFrame({
    "t": np.arange(1, T + 1),
    "solar_cf": solar * DT,
    "hh_a": household_group(1, 43.2),        # Nanogrid 1 in every scenario
    "hh_b": household_group(2, 43.2 * 0.95), # extra household groups for the
    "hh_c": household_group(3, 43.2 * 1.04), # homogeneous-demand scenarios 1 and 3
    "streetlights": streetlights(29.2),
    "school": school(4, 21.5),
})
df.round(5).to_csv("data/profiles.csv", index=False)

print(df.drop(columns="t").sum().round(2).to_string())


def sdi(D):
    J = D.shape[1]
    vals = [1 - D[:, j] @ D[:, k] / np.linalg.norm(D[:, j]) / np.linalg.norm(D[:, k])
            for j in range(J) for k in range(j + 1, J)]
    return float(np.mean(vals))


def pdi(D):
    return float(1 - D.sum(axis=1).max() / D.max(axis=0).sum())


het = df[["hh_a", "streetlights", "school"]].to_numpy()
hom = df[["hh_a", "hh_b", "hh_c"]].to_numpy()
print(f"heterogeneous demand: SDI={sdi(het):.2f} PDI={pdi(het):.2f}   (paper: 0.48, 0.28)")
print(f"homogeneous demand:   SDI={sdi(hom):.2f} PDI={pdi(hom):.2f}   (paper: 0.07, 0.04)")
print("sum of squared demand (Cournot check, paper implies ~5.7):", round(float((het ** 2).sum()), 2))
print("mean daily solar yield (kWh/kWp):", round(df.solar_cf.sum() / DAYS, 2))
