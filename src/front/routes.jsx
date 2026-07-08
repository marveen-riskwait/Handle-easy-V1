import { createBrowserRouter, createRoutesFromElements, Route, Navigate } from "react-router-dom";

import { StaffLayout } from "./layouts/StaffLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";
import { TableDetail } from "./pages/TableDetail";
import { GuestTable } from "./pages/GuestTable";

export const router = createBrowserRouter(
  createRoutesFromElements(
    <Route errorElement={<div className="p-5 text-center">Page introuvable.</div>}>
      {/* Public guest flow — reached by scanning a table QR code */}
      <Route path="/table/:token" element={<GuestTable />} />

      {/* Staff auth */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Staff app (protected, shares a chrome/navbar) */}
      <Route element={<ProtectedRoute><StaffLayout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/tables/:tableId" element={<TableDetail />} />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
    </Route>
  )
);
