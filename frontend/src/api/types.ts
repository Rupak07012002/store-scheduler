export type UserRole = "owner" | "store_manager" | "employee";

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  store_id: string | null;
  linked_employee_id: string | null;
}

export interface Store {
  id: string;
  name: string;
  address: string | null;
  footfall_to_staff_ratio: number | null;
  min_staff_floor: number | null;
  avg_transaction_value: number | null;
  is_active: boolean;
}

export interface Employee {
  id: string;
  store_id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  hire_date: string | null;
  employment_type: "full_time" | "part_time";
  wage_rate: number | null;
  is_active: boolean;
}

export interface ShiftTemplate {
  id: string;
  store_id: string;
  name: string;
  start_time: string;
  end_time: string;
  day_of_week: number | null;
  is_active: boolean;
}

export interface Availability {
  id: string;
  employee_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_available: boolean;
  effective_from: string | null;
  effective_until: string | null;
}

export interface TimeOffRequest {
  id: string;
  employee_id: string;
  start_date: string;
  end_date: string;
  reason: string | null;
  status: "pending" | "approved" | "denied";
}

export interface HeadcountRequirement {
  date: string;
  shift_template_id: string;
  shift_template_name: string;
  predicted_footfall: number;
  required_headcount: number;
}

export interface ShiftAssignment {
  id: string;
  employee_id: string;
  shift_template_id: string;
  date: string;
  status: "proposed" | "edited" | "published";
  manually_edited: boolean;
}

export interface ScheduleRun {
  id: string;
  store_id: string;
  week_start_date: string;
  status: "draft" | "under_review" | "published" | "archived";
  solver_status: "optimal" | "feasible" | "infeasible" | null;
  objective_value: number | null;
  generated_by: string;
  assignments: ShiftAssignment[];
}

export interface ComplianceFlag {
  id: string;
  employee_id: string | null;
  flag_type:
    | "overtime_risk"
    | "insufficient_rest"
    | "understaffed_slot"
    | "overstaffed_slot"
    | "too_many_consecutive_days";
  severity: "hard" | "soft";
  message: string;
  resolved: boolean;
}

export interface SwapRequest {
  id: string;
  source_assignment_id: string;
  target_employee_id: string | null;
  target_assignment_id: string | null;
  status: "pending" | "approved" | "denied" | "cancelled";
}
