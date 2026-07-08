import { Navigate } from "react-router-dom";
import useGlobalReducer from "../hooks/useGlobalReducer";

// Gate staff pages: no stored user → bounce to login.
export function ProtectedRoute({ children }) {
  const { store } = useGlobalReducer();
  if (!store.user) return <Navigate to="/login" replace />;
  return children;
}
