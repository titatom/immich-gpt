import React from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";
import Dashboard from "./pages/Dashboard";
import Review from "./pages/Review";
import Buckets from "./pages/Buckets";
import Prompts from "./pages/Prompts";
import Jobs from "./pages/Jobs";
import Settings from "./pages/Settings";
import Assets from "./pages/Assets";
import Logs from "./pages/Logs";

function Guarded({ children }: { children: React.ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Guarded><Dashboard /></Guarded>} />
        <Route path="review" element={<Guarded><Review /></Guarded>} />
        <Route path="buckets" element={<Guarded><Buckets /></Guarded>} />
        <Route path="prompts" element={<Guarded><Prompts /></Guarded>} />
        <Route path="jobs" element={<Guarded><Jobs /></Guarded>} />
        <Route path="settings" element={<Guarded><Settings /></Guarded>} />
        <Route path="assets" element={<Guarded><Assets /></Guarded>} />
        <Route path="logs" element={<Guarded><Logs /></Guarded>} />
      </Route>
    </Routes>
  );
}
