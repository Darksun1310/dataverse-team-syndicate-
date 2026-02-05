VelocityMart
Operational Recovery & Forensic Audit
Team Syndicate | Bangalore Dark Store Turnaround

This repository documents an end-to-end forensic audit, recovery strategy, and optimization pipeline developed to prevent operational seizure at VelocityMart’s Bangalore fulfillment facility.

The work combines data integrity restoration, constraint-aware optimization, and physical flow analysis to convert a failing dark store into a stable, scalable operation.

📊 Executive Impact (What Changed)

Operational Entropy Reduced: Achieved an 82.2% reduction in systemic chaos across picking, slotting, and compliance.

Inventory Secured: Resolved 464 temperature violations, preventing loss of $8,400 in at-risk inventory.

Fulfillment Performance Restored: Projected recovery to the 3.8-minute gold standard from a 6.2-minute peak.

Future-Ready: Stress-tested and validated for a 20% demand surge (up to 523,262 orders).

🔍 Forensic Findings (Root Causes)

The audit surfaced three non-obvious failure modes silently degrading performance:

1. The Shortcut Paradox

GPS telemetry exposed Picker 07 bypassing safety barriers, producing 671 documented anomalies.
Short-term speed gains created long-term congestion and safety risk.

2. Decimal Drift

Identified 22 SKUs with incorrect weight precision.
These errors triggered false overload alerts, compounding congestion and restocking delays.

3. The Forklift Dead-Zone

Aisle B was quantified as a physical bottleneck, where picker density directly blocked mechanical restocking—collapsing throughput during peak windows.

🛠️ Analytical Pipeline (How It Was Fixed)

Each module maps directly to a recovery objective:

clean.py
Restores data integrity by normalizing units and eliminating “Ghost Bins” from transactional logs.

calculate_metrics.py
Computes the proprietary Chaos Score, translating operational disorder into a measurable signal.

optimize_slotting.py
Generates the top 50 highest-impact SKU relocations within fixed labor and time budgets.

validate_plan.py
Enforces 100% compliance with hard constraints (temperature, weight, aisle access).

📁 Repository Structure
├── data/
│   ├── final_slotting_plan.csv      # Week 91 master layout
│   └── exhibits/                    # Forensic evidence (Picker 07, Decimal Drift)
├── scripts/
│   ├── clean.py                     # Data integrity pipeline
│   ├── calculate_metrics.py         # Chaos Score engine
│   └── optimize_slotting.py         # Constraint-aware optimizer
├── report/
│   └── Report_Syndicate.pdf         # Final forensic audit (LaTeX)
└── README.md
🚀 Strategic Roadmap — Phase 1

The intervention targets the unspoken physics of the facility.

Rather than increasing labor, the strategy restores flow by:

Thinning Aisle B to unblock mechanical restocking

Enforcing thermal compliance at the slotting level

Rebalancing SKU density to absorb peak-hour shocks

This approach stabilizes throughput without exceeding labor or compliance constraints.


All scripts are deterministic and constraint-validated for repeatable execution.
