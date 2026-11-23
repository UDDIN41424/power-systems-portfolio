"""Project 1: Short-circuit levels and overcurrent protection sensitivity in a
medium-voltage grid when the upstream grid weakens (less synchronous generation).

Network : CIGRE medium-voltage benchmark grid (pandapower), 20 kV, radial operation.
Method  : IEC 60909 short-circuit calculation (pandapower.shortcircuit).
Baseline: strong upstream grid (S_sc = 5000 MVA), classic fixed overcurrent setting.
Scenario: weaker upstream grid, with and without inverter-based DER.
"""
import warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import copy
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandapower as pp
import pandapower.networks as pn
import pandapower.shortcircuit as sc

OUT = Path(__file__).resolve().parents[1] / "results"
OUT.mkdir(exist_ok=True)

K_DER = 1.1          # inverter fault current limit, p.u. of rated current (typical grid code range 1.0-1.5)
S_SC_LEVELS = [5000, 2500, 1000, 500]   # MVA upstream short-circuit power at 110 kV
DER_SCALES = [0, 1, 20]                  # PV scaling: 0 = no DER, 1 = CIGRE default, 20 = high penetration (~4 MW PV)
FEEDER_SEND_BUS = 1                      # feeder 1 relay sits at bus 1 (start of Line 1-2)
RELAY_LINE = 0                           # Line 1-2
K_PICKUP = 1.3                           # pickup = 1.3 x max feeder load current (common rule of thumb)
SENS_MIN = 1.5                           # required Ik_min / pickup (sensitivity criterion)

def build(s_sc, der_scale):
    net = pn.create_cigre_network_mv(with_der="pv_wind")
    net.ext_grid["s_sc_max_mva"] = s_sc
    net.ext_grid["s_sc_min_mva"] = s_sc * 0.8   # minimum case: 80 % of maximum
    net.ext_grid["rx_max"] = 0.1; net.ext_grid["rx_min"] = 0.1
    net.line["endtemp_degree"] = 80.0           # conductor end temperature for min-case R (IEC 60909)
    is_pv = net.sgen["name"].str.startswith("PV")
    net.sgen["scaling"] = np.where(is_pv, float(der_scale), 1.0 if der_scale else 0.0)  # scale PV only; wind fixed
    net.sgen["sn_mva"] = net.sgen["p_mw"] * net.sgen["scaling"] / 0.95   # pandapower SC ignores "scaling": encode it in sn_mva
    net.sgen["in_service"] = net.sgen["scaling"] > 0
    net.sgen["k"] = K_DER
    net.sgen["type"] = np.where(net.sgen["name"].str.contains("WKA"), "wind", "pv")
    net.sgen["kappa"] = 1.0
    net.sgen["generator_type"] = "current_source"
    return net

def run(s_sc, der_scale):
    net = build(s_sc, der_scale)
    pp.runpp(net)
    imax_load = net.res_line.at[RELAY_LINE, "i_ka"]
    out = {}
    for case in ("max", "min"):
        n = copy.deepcopy(net)
        sc.calc_sc(n, case=case, fault="3ph", branch_results=True, ip=False, ith=False)
        out[case] = n
    return net, out, imax_load

# Classic setting: derived ONCE from the baseline (strong grid, no DER) and never re-tuned
_n, _, _i = run(5000, 0)
PICKUP_FIXED_KA = K_PICKUP * _i
print(f"Fixed pickup from baseline: {PICKUP_FIXED_KA:.3f} kA")
rows = []
for s in S_SC_LEVELS:
    for d in DER_SCALES:
        net, scn, i_load = run(s, d)
        ikmax = scn["max"].res_bus_sc["ikss_ka"]
        ikmin = scn["min"].res_bus_sc["ikss_ka"]
        # relay at start of feeder; far end = bus 6 (end of feeder 1)
        far = 6
        i_relay_min = scn["min"].res_line_sc.at[RELAY_LINE, "ikss_ka"] if "res_line_sc" in scn["min"] else np.nan
        ik_far_min = ikmin.at[far]
        pickup = PICKUP_FIXED_KA if PICKUP_FIXED_KA else K_PICKUP * i_load
        # fault current seen by the relay for a far-end fault (grid contribution only; DER adds downstream)
        rows.append(dict(s_sc_mva=s, der_scale=d,
            ik_bus1_max_ka=ikmax.at[1], ik_bus6_max_ka=ikmax.at[far],
            ik_bus6_min_ka=ik_far_min, i_relay_far_min_ka=i_relay_min,
            load_ka=i_load, pickup_ka=pickup,
            sensitivity=i_relay_min/pickup if i_relay_min==i_relay_min else np.nan,
            ok=(i_relay_min/pickup >= SENS_MIN) if i_relay_min==i_relay_min else None,
            scr_bus7=(1e3*ikmin.at[7]*20*np.sqrt(3)/1e3) / max(net.sgen.loc[net.sgen.bus==7,"p_mw"].sum(),1e-9) if d>0 else np.nan))
df = pd.DataFrame(rows).round(3)
df.to_csv(OUT/"results.csv", index=False)
print(df.to_string())

# Plot 1: fault level at bus 6 vs upstream strength
fig, ax = plt.subplots(figsize=(7,4.2))
for d in DER_SCALES:
    s = df[df.der_scale==d]
    ax.plot(s.s_sc_mva, s.ik_bus6_min_ka, "o-", label=f"Ik'' min, DER x{d}")
ax.invert_xaxis(); ax.set_xscale("log")
ax.set_xlabel("Upstream short-circuit power at 110 kV (MVA)  ← weaker grid")
ax.set_ylabel("Ik'' at feeder end, bus 6 (kA)")
ax.set_title("CIGRE MV grid: 3-phase fault level at feeder end (IEC 60909)")
ax.grid(alpha=.3); ax.legend()
fig.tight_layout(); fig.savefig(OUT/"fault_level_vs_grid_strength.png", dpi=160)

# Plot 2: relay sensitivity
fig, ax = plt.subplots(figsize=(7,4.2))
for d in DER_SCALES:
    s = df[df.der_scale==d]
    ax.plot(s.s_sc_mva, s.sensitivity, "o-", label=f"DER x{d}")
ax.axhline(SENS_MIN, color="r", ls="--", label=f"required ≥ {SENS_MIN}")
ax.invert_xaxis(); ax.set_xscale("log")
ax.set_xlabel("Upstream short-circuit power (MVA)  ← weaker grid")
ax.set_ylabel("Ik''min at relay / pickup")
ax.set_title("Overcurrent relay sensitivity, feeder 1 (far-end fault)")
ax.grid(alpha=.3); ax.legend()
fig.tight_layout(); fig.savefig(OUT/"relay_sensitivity.png", dpi=160)
