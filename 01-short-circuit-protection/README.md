# 01 – Short-circuit levels and overcurrent protection in a weakening MV grid

**Question:** As synchronous generation leaves the system, the upstream grid gets weaker (lower short-circuit power) and inverter-based DER (PV, wind) increases. Does a conventional fixed overcurrent setting on a 20 kV feeder still work?

Research context: system strength and protection with high inverter-based resource shares is an active topic in Austria and Europe, e.g. the AIT / TU Wien / APG project *Power System Security 2030+* (Symposium Energieinnovation 2026).

## Method
- Network: CIGRE medium-voltage benchmark grid (pandapower), 20 kV, 25 MVA 110/20 kV transformers, radial operation (S1–S3 open).
- Calculation: IEC 60909 three-phase short circuit with `pandapower.shortcircuit` (Ik'' max and min), cable end temperature 80 °C for the minimum case.
- DER: modelled as current sources with a fault current limit of 1.1 p.u. (typical grid-code range 1.0–1.5).
- **Baseline (standard operation):** strong upstream grid (5000 MVA), no DER, classic overcurrent setting: pickup = 1.3 × maximum feeder load current, set once and not re-tuned.
- **Scenarios:** upstream short-circuit power 5000 / 2500 / 1000 / 500 MVA × PV scaling 0 / 1 / 20 (≈ 4 MW PV on feeder 1).
- Criterion: relay sensitivity = Ik'' min (far-end fault, feeder 1) / pickup ≥ 1.5.

## Results (`results/results.csv`, plots in `results/`)
| Upstream S_sc | Ik'' max bus 1 (no DER → PV x20) | Ik'' min bus 6 | Sensitivity |
|---|---|---|---|
| 5000 MVA | 6.48 → 6.67 kA | 1.04 kA | 5.6 |
| 500 MVA | 4.62 → 4.81 kA | 0.97 kA | 5.2 |

- Weakening the 110 kV grid tenfold lowers the maximum fault current at the MV busbar by about 28 % but the far-end minimum fault current by only about 7 %.
- Reason: the 25 MVA, 12 % transformer (≈ 208 MVA) and the cable impedance dominate the fault impedance, not the upstream grid.
- High PV share raises Ik'' max by about 3 %; the minimum case, as in IEC 60909, excludes DER, so sensitivity is unchanged.
- The fixed setting stays sensitive (> 5, requirement 1.5) in every scenario. Short-circuit ratio at the wind bus stays above 20, so it is a strong connection.

**Conclusion:** in this benchmark MV grid, grid weakening alone does not break a classic overcurrent scheme. Problems are more likely with long weak feeders, higher DER shares on the same feeder (infeed/blinding), grid-code current limits close to 1.0 p.u., and at lower voltage levels. These are the next steps.

## Limitations (stated honestly)
- Benchmark grid, not a real utility network: "realistic, not real" data. Parameters follow CIGRE Task Force C6.04.02.
- Three-phase faults only; no earth faults, no relay time grading, no dynamic (EMT) inverter behaviour.
- DER fault current is a simple limited current source; real inverter control (grid-code fault ride-through) is more complex.
- pandapower branch results are marked beta for transformers; bus results were used for the conclusions.

## Run
```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/run_study.py
```

## References
- IEC 60909-0: Short-circuit currents in three-phase a.c. systems.
- CIGRE Task Force C6.04.02, benchmark systems for network integration of renewable and distributed energy resources.
- pandapower documentation (shortcircuit module), Fraunhofer IEE / University of Kassel.
- AIT / TU Wien / APG: Power System Security 2030+ (Symposium Energieinnovation, Graz, 2026).
