import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, errMsg } from "../services/api";

export function Dashboard() {
  const navigate = useNavigate();
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newNumber, setNewNumber] = useState("");

  const load = async () => {
    try {
      const { data } = await api.get("/tables");
      setTables(data);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const addTable = async (e) => {
    e.preventDefault();
    if (!newNumber) return;
    try {
      await api.post("/tables", { table_number: newNumber });
      setNewNumber("");
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  };

  const deleteTable = async (e, t) => {
    e.stopPropagation(); // don't trigger the tile's navigate
    if (!window.confirm(`Supprimer la table ${t.table_number} ?`)) return;
    try {
      await api.delete(`/tables/${t.id}`);
      load();
    } catch (err) {
      setError(errMsg(err));
    }
  };

  if (loading) return <p>Chargement…</p>;

  return (
    <>
      <div className="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
        <h2 className="mb-0">Tables</h2>
        <form className="d-flex gap-2" onSubmit={addTable}>
          <input className="form-control" style={{ width: 140 }}
                 placeholder="N° de table" value={newNumber}
                 onChange={(e) => setNewNumber(e.target.value)} />
          <button className="btn btn-he">Ajouter</button>
        </form>
      </div>

      {error && <div className="alert alert-danger py-2">{error}</div>}

      {tables.length === 0 ? (
        <p className="text-muted">Aucune table. Ajoutez-en une pour commencer.</p>
      ) : (
        <div className="row g-3">
          {tables.map((t) => (
            <div className="col-6 col-md-4 col-lg-3" key={t.id}>
              <div className="card table-tile h-100 position-relative"
                   onClick={() => navigate(`/tables/${t.id}`)}>
                <button type="button" title="Supprimer la table"
                        className="btn btn-sm btn-outline-danger position-absolute top-0 end-0 m-1 lh-1 py-0 px-2"
                        onClick={(e) => deleteTable(e, t)}>×</button>
                <div className="card-body text-center">
                  <div className="display-6 fw-bold">{t.table_number}</div>
                  <span className={`badge ${t.status === "occupied" ? "bg-warning text-dark" : "bg-success"}`}>
                    {t.status === "occupied" ? "Occupée" : "Libre"}
                  </span>
                  {t.active_session_id && (
                    <div className="small text-muted mt-2">Session #{t.active_session_id}</div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
