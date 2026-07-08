import { Outlet, Link, useNavigate } from "react-router-dom";
import useGlobalReducer from "../hooks/useGlobalReducer";
import { api, clearSession } from "../services/api";

export function StaffLayout() {
  const { store, dispatch } = useGlobalReducer();
  const navigate = useNavigate();

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      /* ignore — clear locally regardless */
    }
    clearSession();
    dispatch({ type: "logout" });
    navigate("/login");
  };

  return (
    <>
      <nav className="navbar navbar-dark he-navbar px-3">
        <Link to="/dashboard" className="navbar-brand he-brand mb-0 h1">
          Handle<span>Easy</span>
        </Link>
        <div className="d-flex align-items-center gap-3">
          <span className="text-white-50 small d-none d-sm-inline">
            {store.user?.email}
          </span>
          <button className="btn btn-outline-light btn-sm" onClick={logout}>
            Déconnexion
          </button>
        </div>
      </nav>
      <div className="container py-4">
        <Outlet />
      </div>
    </>
  );
}
