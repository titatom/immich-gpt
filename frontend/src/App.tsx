import React from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Review from "./pages/Review";
import Buckets from "./pages/Buckets";
import Prompts from "./pages/Prompts";
import Jobs from "./pages/Jobs";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="review" element={<Review />} />
        <Route path="buckets" element={<Buckets />} />
        <Route path="prompts" element={<Prompts />} />
        <Route path="jobs" element={<Jobs />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
