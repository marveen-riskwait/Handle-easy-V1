import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import useGlobalReducer from "../hooks/useGlobalReducer";
import { api, setSession, errMsg } from "../services/api";

export function Register() {
  const { dispatch } = useGlobalReducer();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    company_name: "", firstname: "", lastname: "", email: "", password: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", form);
      setSession(data.user, data.csrf_token);
      dispatch({ type: "set_user", payload: data.user });
      navigate("/dashboard");
    } catch (err) {
      setError(errMsg(err, "Inscription impossible"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ maxWidth: 480 }}>
      <div className="text-center py-4">
        <h1 className="he-brand" style={{ color: "var(--he-dark)" }}>
          Handle<span style={{ color: "var(--he-primary)" }}>Easy</span>
        </h1>
        <p className="text-muted">Créez votre restaurant</p>
      </div>
      <div className="card shadow-sm">
        <div className="card-body">
          {error && <div className="alert alert-danger py-2">{error}</div>}
          <form onSubmit={submit}>
            <label className="form-label">Nom du restaurant</label>
            <input className="form-control mb-3" required
                   value={form.company_name} onChange={set("company_name")} />
            <div className="row">
              <div className="col">
                <label className="form-label">Prénom</label>
                <input className="form-control mb-3"
                       value={form.firstname} onChange={set("firstname")} />
              </div>
              <div className="col">
                <label className="form-label">Nom</label>
                <input className="form-control mb-3"
                       value={form.lastname} onChange={set("lastname")} />
              </div>
            </div>
            <label className="form-label">Email</label>
            <input type="email" className="form-control mb-3" required
                   value={form.email} onChange={set("email")} />
            <label className="form-label">Mot de passe</label>
            <input type="password" className="form-control mb-3" required minLength={6}
                   value={form.password} onChange={set("password")} />
            <button className="btn btn-he w-100" disabled={loading}>
              {loading ? "…" : "Créer le compte"}
            </button>
          </form>
          <p className="text-center mt-3 mb-0 small">
            Déjà inscrit ? <Link to="/login">Se connecter</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
