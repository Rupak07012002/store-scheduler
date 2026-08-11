from app.models.employee import Employee

DEFAULT_HOURLY_WEIGHT_CENTS = 100  # $1.00/hr placeholder weight when no wage data exists


def objective_weight_cents_per_hour(employee: Employee) -> int:
    """
    Returns the per-hour weight (in cents) used in the optimizer's objective.

    v1 (confirmed with owner: no wage data yet): every employee gets the
    same constant weight, so minimizing sum(weight * hours) is mathematically
    equivalent to minimizing total scheduled hours - a proxy for cost.

    v1.1 seam: once Employee.wage_rate is populated, this same function
    starts returning true wage-based weights and the optimizer objective
    becomes real labor-cost minimization, with no change needed anywhere
    else (see docs/scaling-guide.md).
    """
    if employee.wage_rate is not None:
        return int(round(float(employee.wage_rate) * 100))
    return DEFAULT_HOURLY_WEIGHT_CENTS
