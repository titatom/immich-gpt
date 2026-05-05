import React from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./contexts/AuthContext";
import Dashboard from "./pages/Dashboard";
import Routing from "./pages/Routing";
import RoutingPlans from "./pages/RoutingPlans";
import Jobs from "./pages/Jobs";
import Settings from "./pages/Settings";
import Assets from "./pages/Assets";
import Logs from "./pages/Logs";
import Login from "./pages/Login";
import Setup from "./pages/Setup";
import ForcePasswordChange from "./pages/ForcePasswordChange";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import AdminUsers from "./pages/AdminUsers";

function Guarded({ children }: { children: React.ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public routes */}
        <Route path="/setup" element={<Setup />} />
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/change-password" element={<ForcePasswordChange />} />

        {/* Protected app routes */}
        <Route path="/" element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }>
          <Route index element={<Guarded><Dashboard /></Guarded>} />
          <Route path="assets" element={<Guarded><Assets /></Guarded>} />
          <Route path="routing" element={<Guarded><Routing /></Guarded>} />
          <Route path="routing/plans" element={<Guarded><RoutingPlans /></Guarded>} />
          <Route path="jobs" element={<Guarded><Jobs /></Guarded>} />
          <Route path="logs" element={<Guarded><Logs /></Guarded>} />
          <Route path="settings" element={<Guarded><Settings /></Guarded>} />

          {/* Admin-only routes */}
          <Route path="admin/users" element={
            <ProtectedRoute requireAdmin>
              <Guarded><AdminUsers /></Guarded>
            </ProtectedRoute>
          } />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
