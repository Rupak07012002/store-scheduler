# Forecasting & Optimization, Explained Plainly

This is the "AI" part of the system, broken into the two pieces that actually do the thinking: **predicting demand**, and **turning that prediction into a legal, feasible schedule**. Both are written to be explainable - if you can't answer "why did it suggest this," it's not trustworthy enough to run a business on.

## Part 1: Predicting footfall (`app/services/forecasting/seasonal_baseline.py`)

### The core idea

For a given store, shift ("Morning"/"Afternoon"/"Evening"), and target date, the model asks: **"What have similar days looked like recently?"**

Concretely, for a Saturday afternoon three weeks from now, it looks at:

1. **The full history of Saturday afternoons** at this store (the "baseline seasonality" - Saturdays are probably always busier than Tuesdays, so this captures that pattern).
2. **Just the last 14 days' worth of Saturday afternoons** (the "recent trend" - if the store has been getting steadily busier lately, this catches that faster than the full history would).

It then blends them: 60% recent, 40% full-history. If there's no recent data for that day/shift combination yet, it just uses the full history. If there's no history *at all* yet (a brand-new store), it falls back to that shift's average across all days, ignoring day-of-week, so it still produces a usable number rather than a zero.

Finally, it multiplies by a **holiday multiplier** if the target date is in the `holiday_calendar_entries` table (e.g. 2.2x on Black Friday) - because no amount of historical averaging predicts a one-off event; that's a judgment call an owner enters directly.

### Why not a "real" machine learning model?

Models like Prophet or gradient-boosted trees genuinely predict better - *given enough data*. With only weeks-to-months of real history (confirmed with the store owner) and 8 stores' worth of independent seasonality to learn, those models would either underfit or overfit in ways that are hard to detect without a much larger evaluation dataset than exists yet. A simple average is honest about its confidence and - just as important - lets you *ask it why*: "why does it think Saturday afternoon needs 2 people" has the plain answer "that's what Saturday afternoons have recently averaged," not a shrug at 40,000 model weights.

**The upgrade path is deliberate and already wired in**: `app/services/forecasting/interface.py` defines a `Forecaster` protocol that `SeasonalBaselineForecaster` implements. Once 12+ months of real Shopify data exist, a `ProphetForecaster` (or similar) implementing the same `predict_week(...)` method can be swapped in without touching the labor-requirement translation, the optimizer, or any API route.

### From footfall to "how many people do we need"

`app/services/labor_requirements.py` does one small, deliberately transparent calculation:

```
required_headcount = max(min_staff_floor, ceil(predicted_footfall / footfall_to_staff_ratio))
```

`footfall_to_staff_ratio` (e.g., "25 customers/hour per staff member") and `min_staff_floor` (e.g., "always have at least 1 person") are **owner-tunable settings per store**, not something the model learns - because "how many customers can one staff member reasonably serve per hour" is a business judgment about service quality, not a fact hiding in the data.

## Part 2: Turning demand into a schedule (`app/services/optimization/cp_sat_model.py`)

### Why a shift-template model, not arbitrary time blocks

Each store defines a small number of fixed shift templates (typically Morning/Afternoon/Evening) rather than letting the solver pick arbitrary start/end times. Three reasons:

1. **It's how retail actually staffs.** Shifts have fixed handoff/break boundaries in practice; nobody schedules someone 9:17am-2:43pm.
2. **It keeps the model small and fast.** With ~30 employees, 7 days, and 3 templates, there are roughly 630 possible assignments to decide on - trivial for a constraint solver to explore exhaustively in under a second. Arbitrary continuous time slots would blow that number up by orders of magnitude for no real benefit.
3. **It's explainable.** An owner reviewing a draft schedule reasons in terms of "who's on Morning Tuesday," not an abstract time interval.

### The model, in plain terms

For every (employee, day, shift template) combination where that employee is actually available, the solver has one yes/no decision to make: *is this person working this shift?* That's the entire "decision variable" set - roughly 30 x 7 x 3 = 630 yes/no questions per store, per week.

It answers all of them at once, subject to rules:

- **Coverage**: each (day, shift) slot must have at least as many people assigned as the forecast says is needed - *unless it's truly impossible* (not enough available staff), in which case the solver is allowed to fall short rather than fail outright, and that shortfall gets flagged for a human to see (see the Compliance section below).
- **One shift per day per employee**: nobody works Morning and Evening the same day in v1 (a documented simplification, not a hard technical limit).
- **Weekly hours cap, softly enforced**: going over the configured overtime threshold is *allowed* (retail sometimes genuinely needs it) but *penalized* in the math below, so the solver only does it when there's no better option - and it always shows up as a flag afterward.
- **Minimum rest between shifts**: if working an Evening shift on Monday and a Morning shift on Tuesday wouldn't leave enough hours to rest (per your configured minimum), the solver simply isn't allowed to assign both to the same person.
- **Maximum consecutive working days**: nobody is scheduled for more days in a row than your configured limit, checked across any rolling window in the week.

Given all of that, it picks the specific yes/no answers that **minimize total scheduled hours** (today's cost proxy, since no wage data exists yet - see below) **while heavily penalizing any coverage shortfall and moderately penalizing overtime**. "Heavily" and "moderately" are deliberate: the solver will accept some overtime to avoid leaving a shift completely uncovered, but it will never leave a shift uncovered just to dodge a little overtime.

### Why "minimize hours" and not "minimize cost"?

True labor-cost minimization needs a wage rate per employee, which doesn't exist yet (confirmed with the owner). Rather than fake a number, v1 minimizes total scheduled *hours* - a reasonable proxy, since fewer scheduled hours generally means lower payroll even without knowing exact rates. The moment `Employee.wage_rate` is populated for real, `app/services/optimization/cost.py::objective_weight_cents_per_hour` starts using it automatically, and the optimizer starts minimizing real dollars instead - no other code changes.

### What happens when it's genuinely infeasible

If there simply aren't enough available, rested, under-the-overtime-cap employees to cover every required slot, the solver doesn't give up - it finds the best schedule it can, marks exactly which slots are short-staffed and by how many people, and hands that to the compliance checker, which turns it into a **hard** flag that blocks publishing until a manager either accepts the shortfall's real-world consequences or manually resolves it (e.g., by calling in extra help, adjusting availability, or accepting reduced coverage for that slot).

## Compliance flags: the safety net

After every solve *and* after every manual edit a manager makes, `app/services/compliance.py` independently re-derives every flag from the schedule's actual current state - it doesn't trust that the solver's guarantees still hold once a human has changed something. This is what catches a manager accidentally re-introducing a rest violation while fixing something else. Flags are either:

- **Hard** (understaffing, insufficient rest, too many consecutive days) - publishing is blocked until resolved.
- **Soft** (overtime risk, overstaffing) - shown for awareness, doesn't block publishing, because sometimes the right call is genuinely to accept a bit of overtime rather than leave a shift short.
