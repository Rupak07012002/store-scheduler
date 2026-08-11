# ADR-002: Fixed shift templates instead of continuous time-block scheduling

## Status
Accepted

## Context
The optimizer needs to decide when each employee works. The two options considered: (a) let the solver choose from a small set of store-defined fixed shift templates (e.g., Morning/Afternoon/Evening), or (b) let it choose an arbitrary start/end time from a continuous range.

## Decision
Fixed, store-configurable shift templates (`ShiftTemplate` table).

## Rationale
- **Problem size**: with ~30 employees, 7 days, and 3 templates, there are ~630 decision variables per store per week - solvable to optimality in well under a second. Continuous time blocks would require discretizing into much finer intervals (e.g., 15-minute blocks), multiplying the variable count by an order of magnitude for a granularity retail scheduling doesn't actually need.
- **Explainability**: a manager reviewing a draft schedule reasons in terms of "who's on Morning Tuesday," not an arbitrary interval like 9:17am-2:43pm.
- **Real-world fit**: retail shifts have fixed handoff and break boundaries in practice; genuinely arbitrary start times aren't how stores actually operate.

## Consequences
- A store that wants finer-grained shift options must add more templates (e.g., a 4th "Mid-day" template), not rely on the solver inventing arbitrary times. This is a data-entry action (via the admin API/UI), not a code change.
- Break timing is handled as a post-solve compliance check against total shift length, not as a solved variable - keeping the model's variable count small. If break *placement* within a shift ever needs to be solved for (not just validated), that would need new decision variables and is a documented gap, not an oversight.
