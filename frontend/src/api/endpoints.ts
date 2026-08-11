import { apiRequest, setTokens } from "./client";
import type {
  Availability,
  ComplianceFlag,
  CurrentUser,
  Employee,
  HeadcountRequirement,
  ScheduleRun,
  ShiftTemplate,
  Store,
  SwapRequest,
  TimeOffRequest,
} from "./types";

export async function login(email: string, password: string): Promise<CurrentUser> {
  const tokens = await apiRequest<{ access_token: string; refresh_token: string }>("/auth/login", {
    method: "POST",
    body: { email, password },
    retry: false,
  });
  setTokens(tokens.access_token, tokens.refresh_token);
  return apiRequest<CurrentUser>("/auth/me");
}

export const getMe = () => apiRequest<CurrentUser>("/auth/me");

export const listStores = () => apiRequest<Store[]>("/stores");
export const getStore = (storeId: string) => apiRequest<Store>(`/stores/${storeId}`);
export const updateStore = (storeId: string, body: Partial<Store>) =>
  apiRequest<Store>(`/stores/${storeId}`, { method: "PATCH", body });

export const listEmployees = (storeId: string) => apiRequest<Employee[]>(`/employees?store_id=${storeId}`);
export const createEmployee = (body: Partial<Employee> & { store_id: string; full_name: string }) =>
  apiRequest<Employee>("/employees", { method: "POST", body });
export const updateEmployee = (employeeId: string, body: Partial<Employee>) =>
  apiRequest<Employee>(`/employees/${employeeId}`, { method: "PATCH", body });

export const listShiftTemplates = (storeId: string) =>
  apiRequest<ShiftTemplate[]>(`/shift-templates?store_id=${storeId}`);
export const createShiftTemplate = (
  storeId: string,
  body: { name: string; start_time: string; end_time: string; day_of_week: number | null },
) => apiRequest<ShiftTemplate>(`/shift-templates?store_id=${storeId}`, { method: "POST", body });

export const listAvailability = (employeeId: string) =>
  apiRequest<Availability[]>(`/availability?employee_id=${employeeId}`);
export const createAvailability = (
  employeeId: string,
  body: { day_of_week: number; start_time: string; end_time: string; is_available: boolean },
) => apiRequest<Availability>(`/availability?employee_id=${employeeId}`, { method: "POST", body });
export const deleteAvailability = (availabilityId: string) =>
  apiRequest<void>(`/availability/${availabilityId}`, { method: "DELETE" });

export const listTimeOff = (employeeId: string) =>
  apiRequest<TimeOffRequest[]>(`/time-off?employee_id=${employeeId}`);
export const createTimeOff = (employeeId: string, body: { start_date: string; end_date: string; reason?: string }) =>
  apiRequest<TimeOffRequest>(`/time-off?employee_id=${employeeId}`, { method: "POST", body });
export const approveTimeOff = (requestId: string) =>
  apiRequest<TimeOffRequest>(`/time-off/${requestId}/approve`, { method: "PATCH" });
export const denyTimeOff = (requestId: string) =>
  apiRequest<TimeOffRequest>(`/time-off/${requestId}/deny`, { method: "PATCH" });

export const getForecast = (storeId: string, weekStart?: string) =>
  apiRequest<HeadcountRequirement[]>(`/forecasts/${storeId}${weekStart ? `?week_start=${weekStart}` : ""}`);

export const listScheduleRuns = (storeId: string) => apiRequest<ScheduleRun[]>(`/schedules?store_id=${storeId}`);
export const getScheduleRun = (runId: string) => apiRequest<ScheduleRun>(`/schedules/${runId}`);
export const generateSchedule = (storeId: string, weekStart: string) =>
  apiRequest<ScheduleRun>("/schedules/generate", { method: "POST", body: { store_id: storeId, week_start: weekStart } });
export const getComplianceFlags = (runId: string) => apiRequest<ComplianceFlag[]>(`/schedules/${runId}/compliance`);
export const addAssignment = (
  runId: string,
  body: { employee_id: string; shift_template_id: string; date: string },
) => apiRequest<ScheduleRun>(`/schedules/${runId}/assignments`, { method: "POST", body });
export const removeAssignment = (runId: string, assignmentId: string) =>
  apiRequest<ScheduleRun>(`/schedules/${runId}/assignments/${assignmentId}`, { method: "DELETE" });
export const publishSchedule = (runId: string) =>
  apiRequest<ScheduleRun>(`/schedules/${runId}/publish`, { method: "POST" });

export const myShifts = () => apiRequest<import("./types").ShiftAssignment[]>("/me/shifts");

export const requestSwap = (body: {
  source_assignment_id: string;
  target_employee_id?: string;
  target_assignment_id?: string;
}) => apiRequest<SwapRequest>("/swaps", { method: "POST", body });
export const listSwaps = (storeId: string, status?: string) =>
  apiRequest<SwapRequest[]>(`/swaps?store_id=${storeId}${status ? `&status=${status}` : ""}`);
export const approveSwap = (swapId: string) => apiRequest<SwapRequest>(`/swaps/${swapId}/approve`, { method: "PATCH" });
export const denySwap = (swapId: string) => apiRequest<SwapRequest>(`/swaps/${swapId}/deny`, { method: "PATCH" });
