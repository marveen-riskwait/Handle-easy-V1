import { createBrowserRouter, createRoutesFromElements, Route } from "react-router-dom";

import { PublicLayout } from "./components/PublicLayout";
import { Catalog } from "./pages/Catalog";
import { StaffLayout } from "./layouts/StaffLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";

export const router = createBrowserRouter(
  createRoutesFromElements(
    <Route errorElement={<div className="p-5 text-center">Page introuvable.</div>}>
      {/* Public visitor site */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Catalog />} />
      </Route>

      {/* Staff auth */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Staff app (protected, shares a chrome/navbar) */}
      <Route element={<ProtectedRoute><StaffLayout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<Dashboard />} />
      </Route>
    </Route>
  )
);
