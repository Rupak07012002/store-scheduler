import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import PrivateRoute from "./components/PrivateRoute";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import HomeRedirect from "./pages/HomeRedirect";
import StoresPage from "./pages/StoresPage";
import StoreDashboardPage from "./pages/StoreDashboardPage";
import ScheduleReviewPage from "./pages/ScheduleReviewPage";
import SwapsPage from "./pages/SwapsPage";
import MyShiftsPage from "./pages/MyShiftsPage";
import AvailabilityPage from "./pages/AvailabilityPage";
import TimeOffPage from "./pages/TimeOffPage";
import RequestSwapPage from "./pages/RequestSwapPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Layout />
              </PrivateRoute>
            }
          >
            <Route index element={<HomeRedirect />} />
            <Route path="stores" element={<StoresPage />} />
            <Route path="stores/:storeId" element={<StoreDashboardPage />} />
            <Route path="schedules/:runId" element={<ScheduleReviewPage />} />
            <Route path="swaps" element={<SwapsPage />} />
            <Route path="my-shifts" element={<MyShiftsPage />} />
            <Route path="availability" element={<AvailabilityPage />} />
            <Route path="time-off" element={<TimeOffPage />} />
            <Route path="request-swap" element={<RequestSwapPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
