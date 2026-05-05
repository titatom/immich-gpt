import React, { Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./contexts/AuthContext";

const Dashboard = React.lazy(() => import("./pages/Dashboard"));
const Routing = React.lazy(() => import("./pages/Routing"));
const RoutingPlans = React.lazy(() => import("./pages/RoutingPlans"));
const Jobs = React.lazy(() => import("./pages/Jobs"));
const Settings = React.lazy(() => import("./pages/Settings"));
const Assets = React.lazy(() => import("./pages/Assets"));
const Logs = React.lazy(() => import("./pages/Logs"));
const Login = React.lazy(() => import("./pages/Login"));
const Setup = React.lazy(() => import("./pages/Setup"));
const ForcePasswordChange = React.lazy(() => import("./pages/ForcePasswordChange"));
const ForgotPassword = React.lazy(() => import("./pages/ForgotPassword"));
const ResetPassword = React.lazy(() => import("./pages/ResetPassword"));
const AdminUsers = React.lazy(() => import("./pages/AdminUsers"));

function Guarded({ children }: { children: React.ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>;
}

function PageFallback() {
  return (
    <div style={{ padding: 32, color: "#64748b", fontSize: 14 }}>
      Loading…
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public routes */}
        <Route path="/setup" element={<Suspense fallback={<PageFallback />}><Setup /></Suspense>} />
        <Route path="/login" element={<Suspense fallback={<PageFallback />}><Login /></Suspense>} />
        <Route path="/forgot-password" element={<Suspense fallback={<PageFallback />}><ForgotPassword /></Suspense>} />
        <Route path="/reset-password" element={<Suspense fallback={<PageFallback />}><ResetPassword /></Suspense>} />
        <Route path="/change-password" element={<Suspense fallback={<PageFallback />}><ForcePasswordChange /></Suspense>} />

          {/* Protected app routes */}
          <Route path="/" element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }>
          <Route index element={<Suspense fallback={<PageFallback />}><Guarded><Dashboard /></Guarded></Suspense>} />
          <Route path="assets" element={<Suspense fallback={<PageFallback />}><Guarded><Assets /></Guarded></Suspense>} />
          <Route path="routing" element={<Suspense fallback={<PageFallback />}><Guarded><Routing /></Guarded></Suspense>} />
          <Route path="routing/plans" element={<Suspense fallback={<PageFallback />}><Guarded><RoutingPlans /></Guarded></Suspense>} />
          <Route path="jobs" element={<Suspense fallback={<PageFallback />}><Guarded><Jobs /></Guarded></Suspense>} />
          <Route path="logs" element={<Suspense fallback={<PageFallback />}><Guarded><Logs /></Guarded></Suspense>} />
          <Route path="settings" element={<Suspense fallback={<PageFallback />}><Guarded><Settings /></Guarded></Suspense>} />

            {/* Admin-only routes */}
            <Route path="admin/users" element={
              <ProtectedRoute requireAdmin>
              <Suspense fallback={<PageFallback />}><Guarded><AdminUsers /></Guarded></Suspense>
              </ProtectedRoute>
            } />
          </Route>
        </Routes>
    </AuthProvider>
  );
}
