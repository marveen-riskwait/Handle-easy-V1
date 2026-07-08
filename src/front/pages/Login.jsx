import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import useGlobalReducer from "../hooks/useGlobalReducer";
import { api, setSession, errMsg } from "../services/api";

export function Login() {
  const { dispatch } = useGlobalReducer();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", form);
      setSession(data.user, data.csrf_token);
      dispatch({ type: "set_user", payload: data.user });
      navigate("/dashboard");
    } catch (err) {
      setError(errMsg(err, "Connexion impossible"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ maxWidth: 420 }}>
      <div className="text-center py-4">
        <h1 className="he-brand" style={{ color: "var(--he-dark)" }}>
          Handle<span style={{ color: "var(--he-primary)" }}>Easy</span>
        </h1>
        <p className="text-muted">Espace restaurateur</p>
      </div>
      <div className="card shadow-sm">
        <div className="card-body">
          {error && <div className="alert alert-danger py-2">{error}</div>}
          <form onSubmit={submit}>
            <label className="form-label">Email</label>
            <input type="email" className="form-control mb-3" required
                   value={form.email}
                   onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <label className="form-label">Mot de passe</label>
            <input type="password" className="form-control mb-3" required
                   value={form.password}
                   onChange={(e) => setForm({ ...form, password: e.target.value })} />
            <button className="btn btn-he w-100" disabled={loading}>
              {loading ? "…" : "Se connecter"}
            </button>
          </form>
          <p className="text-center mt-3 mb-0 small">
            Pas encore de compte ? <Link to="/register">Créer un restaurant</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
