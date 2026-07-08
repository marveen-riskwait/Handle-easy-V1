import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api, errMsg } from "../services/api";

export function TableDetail() {
  const { tableId } = useParams();
  const navigate = useNavigate();
  const [table, setTable] = useState(null);
  const [split, setSplit] = useState(null);
  const [openOrders, setOpenOrders] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const loadTable = async () => {
    const { data } = await api.get(`/tables/${tableId}`);
    setTable(data);
    if (data.active_session_id) {
      const s = await api.get(`/sessions/${data.active_session_id}/split`);
      setSplit(s.data);
    } else {
      setSplit(null);
    }
  };

  const loadOpenOrders = async () => {
    try {
      const { data } = await api.get("/odoo/open-orders");
      setOpenOrders(data);
    } catch { /* odoo optional */ }
  };

  useEffect(() => {
    loadTable().catch((e) => setError(errMsg(e)));
    loadOpenOrders();
  }, [tableId]);

  const openSession = async (odooOrderId) => {
    setBusy(true); setError("");
    try {
      await api.post(`/sessions/tables/${tableId}/session`,
        odooOrderId ? { odoo_order_id: odooOrderId } : {});
      await loadTable();
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };

  const importOrder = async (odooOrderId) => {
    setBusy(true); setError("");
    try {
      await api.post(`/sessions/${table.active_session_id}/import`,
        { odoo_order_id: odooOrderId });
      await loadTable();
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };

  const closeSession = async () => {
    setBusy(true); setError("");
    try {
      await api.post(`/sessions/${table.active_session_id}/close`);
      await loadTable();
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };

  const deleteTable = async () => {
    if (!window.confirm(`Supprimer la table ${table.table_number} ? Cette action est définitive.`)) return;
    setBusy(true); setError("");
    try {
      await api.delete(`/tables/${tableId}`);
      navigate("/dashboard");
    } catch (e) { setError(errMsg(e)); setBusy(false); }
  };

  if (!table) return <p>Chargement…</p>;

  const guestUrl = table.qr?.url;

  return (
    <>
      <Link to="/dashboard" className="btn btn-link px-0 mb-2">← Tables</Link>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h2 className="mb-0">Table {table.table_number}</h2>
        <div className="d-flex align-items-center gap-2">
          <span className={`badge ${table.status === "occupied" ? "bg-warning text-dark" : "bg-success"}`}>
            {table.status === "occupied" ? "Occupée" : "Libre"}
          </span>
          <button className="btn btn-outline-danger btn-sm" disabled={busy}
                  onClick={deleteTable}>Supprimer la table</button>
        </div>
      </div>

      {error && <div className="alert alert-danger py-2">{error}</div>}

      <div className="row g-4">
        {/* QR code */}
        <div className="col-md-4">
          <div className="card">
            <div className="card-body text-center">
              <h6 className="text-muted">QR Code de la table</h6>
              {table.qr?.image
                ? <img src={table.qr.image} alt="QR" className="img-fluid" style={{ maxWidth: 200 }} />
                : <p className="small text-muted">QR indisponible</p>}
              {guestUrl && (
                <div className="small text-break mt-2">
                  <a href={guestUrl} target="_blank" rel="noreferrer">{guestUrl}</a>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Session */}
        <div className="col-md-8">
          {!table.active_session_id ? (
            <div className="card">
              <div className="card-body">
                <h5>Aucune session ouverte</h5>
                <p className="text-muted">Ouvrez une session pour démarrer le partage.</p>
                <button className="btn btn-he me-2" disabled={busy}
                        onClick={() => openSession(null)}>
                  Ouvrir une session vide
                </button>
                {openOrders.map((o) => (
                  <button key={o.odoo_order_id} className="btn btn-outline-secondary me-2 mb-2"
                          disabled={busy} onClick={() => openSession(o.odoo_order_id)}>
                    Ouvrir avec commande Odoo #{o.odoo_order_id} (table {o.table_number})
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="card">
              <div className="card-body">
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <h5 className="mb-0">Session #{table.active_session_id}</h5>
                  <button className="btn btn-outline-danger btn-sm" disabled={busy}
                          onClick={closeSession}>Clôturer</button>
                </div>

                {openOrders.length > 0 && (
                  <div className="mb-3">
                    {openOrders.map((o) => (
                      <button key={o.odoo_order_id}
                              className="btn btn-sm btn-outline-secondary me-2"
                              disabled={busy} onClick={() => importOrder(o.odoo_order_id)}>
                        Importer commande Odoo #{o.odoo_order_id}
                      </button>
                    ))}
                  </div>
                )}

                {split && <SplitSummary split={split} />}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function SplitSummary({ split }) {
  if (!split.items.length) {
    return <p className="text-muted mb-0">Aucun article. Importez une commande Odoo.</p>;
  }
  return (
    <>
      <h6 className="text-muted">Articles</h6>
      <ul className="list-group mb-3">
        {split.items.map((it) => (
          <li key={it.id} className="list-group-item d-flex justify-content-between">
            <span>{it.quantity}× {it.name}
              {it.paid && <span className="badge bg-success ms-2">payé</span>}</span>
            <strong>{it.line_total.toFixed(2)} €</strong>
          </li>
        ))}
      </ul>
      <div className="d-flex justify-content-between">
        <span>Total</span><strong>{split.grand_total.toFixed(2)} €</strong>
      </div>
      <div className="d-flex justify-content-between text-success">
        <span>Payé</span><strong>{split.paid_total.toFixed(2)} €</strong>
      </div>
    </>
  );
}
