# ADR-003: Minimize scheduled hours, not labor cost, in v1

## Status
Accepted (with a documented, code-level upgrade path)

## Context
The stated goal is minimizing labor cost while meeting demand. True cost minimization requires a wage rate per employee. The store owner confirmed no wage data exists yet in a usable form.

## Decision
The optimizer's objective minimizes total scheduled hours (weighted equally per employee) rather than dollar cost. `app/services/optimization/cost.py::objective_weight_cents_per_hour` returns a flat placeholder weight for every employee unless `Employee.wage_rate` is populated, in which case it automatically switches to real per-employee weights.

## Rationale
- Fabricating a plausible-looking average wage to "minimize cost" would produce numbers that look precise but aren't grounded in anything real - actively misleading in a dashboard a business owner is making staffing decisions from.
- Minimizing total scheduled hours is a defensible, honest proxy: fewer scheduled hours generally does mean lower payroll even without knowing the exact rate.
- The upgrade path costs nothing extra later: the objective function's *shape* doesn't change, only the per-employee coefficient - populating `wage_rate` is enough.

## Consequences
- The compliance/labor-summary dashboard currently reports scheduled hours, not a dollar figure, and says so explicitly in the UI - it does not claim to show "cost" when it can't back that claim.
- Revenue-side numbers on the same dashboard (`avg_transaction_value * predicted footfall`) are clearly labeled as an estimate for the same reason - Shopify's actual revenue isn't wired up yet either (see `docs/scaling-guide.md` item 1).
