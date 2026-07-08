import { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { api, errMsg } from "../services/api";

// Remember which guest "I am" for a given session, so a reload keeps my
// identity (guests have no login).
const meKey = (sessionId) => `he_customer_${sessionId}`;

export function GuestTable() {
  const { token } = useParams();
  const [data, setData] = useState(null);   // { table, company, session, split, customers }
  const [meId, setMeId] = useState(null);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api.get(`/table/${token}`);
      setData(res.data);
      if (res.data.session) {
        const stored = localStorage.getItem(meKey(res.data.session.id));
        // Only trust the stored id if that customer still exists.
        const exists = (res.data.customers || []).some((c) => String(c.id) === stored);
        setMeId(exists ? Number(stored) : null);
      }
    } catch (e) {
      setError(errMsg(e, "Table introuvable"));
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  // Light polling so a guest sees others' claims/payments arrive.
  useEffect(() => {
    if (!data?.session || data.session.status === "closed") return;
    const id = setInterval(load, 4000);
    return () => clearInterval(id);
  }, [data?.session, load]);

  const join = async (e) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const { data: c } = await api.post(`/sessions/${data.session.id}/customers`,
        { name: name.trim() });
      localStorage.setItem(meKey(data.session.id), String(c.id));
      setMeId(c.id);
      await load();
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };

  // Become an existing guest at the table (no new customer created). Lets
  // one device hop between convives — handy when the phone is passed around.
  const beSomeone = (id) => {
    localStorage.setItem(meKey(data.session.id), String(id));
    setMeId(id);
  };

  // Drop the current identity to pick/join as someone else.
  const switchGuest = () => {
    localStorage.removeItem(meKey(data.session.id));
    setMeId(null);
    setName("");
  };

  const toggleItem = async (item) => {
    if (item.paid || !meId) return;
    const mine = item.assignee_ids.includes(meId);
    setBusy(true);
    try {
      const path = mine ? "unclaim" : "claim";
      const { data: split } = await api.post(
        `/sessions/${data.session.id}/items/${item.id}/${path}`, { customer_id: meId });
      setData((d) => ({ ...d, split }));
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };

  const pay = async () => {
    setBusy(true); setError("");
    try {
      const { data: res } = await api.post(`/sessions/${data.session.id}/pay`,
        { customer_id: meId });
      setData((d) => ({ ...d, split: res.split, session: res.session }));
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };

  if (error && !data) return <Shell><div className="alert alert-danger">{error}</div></Shell>;
  if (!data) return <Shell><p>Chargement…</p></Shell>;

  // No active seating on this table.
  if (!data.session) {
    return (
      <Shell>
        <Header table={data.table} company={data.company} />
        <div className="alert alert-info">
          Aucune session ouverte sur cette table. Demandez à votre serveur d'en ouvrir une.
        </div>
      </Shell>
    );
  }

  // Closed / fully paid.
  if (data.session.status === "closed") {
    return (
      <Shell>
        <Header table={data.table} company={data.company} />
        <div className="text-center py-5">
          <div className="display-1">✓</div>
          <h4>Addition réglée. Merci&nbsp;!</h4>
        </div>
      </Shell>
    );
  }

  // Need to identify who I am.
  if (!meId) {
    const others = data.customers || [];
    return (
      <Shell>
        <Header table={data.table} company={data.company} />
        {error && <div className="alert alert-danger py-2">{error}</div>}

        {others.length > 0 && (
          <div className="card mb-3">
            <div className="card-body">
              <h6 className="text-muted">Déjà à cette table</h6>
              <div className="d-flex flex-wrap gap-2">
                {others.map((c) => (
                  <button key={c.id} className="btn btn-outline-secondary btn-sm"
                          onClick={() => beSomeone(c.id)}>
                    Je suis {c.display_name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="card">
          <div className="card-body">
            <h5>{others.length > 0 ? "Nouveau convive" : "Bienvenue !"}</h5>
            <p className="text-muted">Entrez votre prénom pour rejoindre la table.</p>
            <form onSubmit={join}>
              <input className="form-control mb-3" placeholder="Votre prénom (optionnel)"
                     value={name} onChange={(e) => setName(e.target.value)} />
              <button className="btn btn-he w-100" disabled={busy}>Rejoindre</button>
            </form>
          </div>
        </div>
      </Shell>
    );
  }

  const split = data.split;
  const me = split.customers.find((c) => c.id === meId);
  const customersById = Object.fromEntries(split.customers.map((c) => [c.id, c]));

  return (
    <Shell>
      <Header table={data.table} company={data.company} />
      <div className="d-flex justify-content-between align-items-center mb-2">
        <span className="badge bg-light text-dark border">
          Vous&nbsp;: <strong>{me?.display_name}</strong>
        </span>
        <button className="btn btn-link btn-sm p-0 text-muted" onClick={switchGuest}>
          Changer de convive
        </button>
      </div>
      {error && <div className="alert alert-danger py-2">{error}</div>}

      <p className="text-muted small mb-2">
        Cochez ce que vous avez consommé. Un article partagé se divise entre les convives qui le cochent.
      </p>

      <div className="list-group mb-3">
        {split.items.map((it) => {
          const mine = it.assignee_ids.includes(meId);
          return (
            <button key={it.id} type="button"
                    className={`list-group-item list-group-item-action item-row ${mine ? "claimed" : ""} ${it.paid ? "paid" : ""}`}
                    disabled={it.paid || busy}
                    onClick={() => toggleItem(it)}>
              <div className="d-flex justify-content-between align-items-center">
                <div>
                  <div className="fw-semibold">
                    {mine ? "☑" : "☐"} {it.quantity}× {it.name}
                    {it.paid && <span className="badge bg-success ms-2">payé</span>}
                  </div>
                  <div className="small text-muted">
                    {it.line_total.toFixed(2)} €
                    {it.assignee_ids.length > 1 &&
                      ` · partagé à ${it.assignee_ids.length} → ${it.share.toFixed(2)} €/pers`}
                  </div>
                </div>
                <div>
                  {it.assignee_ids.map((cid) => (
                    <span className="avatar-chip" key={cid}
                          title={customersById[cid]?.display_name}>
                      {(customersById[cid]?.display_name || "?").charAt(0).toUpperCase()}
                    </span>
                  ))}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {split.unassigned_total > 0 && (
        <div className="alert alert-warning py-2 small">
          {split.unassigned_total.toFixed(2)} € d'articles ne sont encore attribués à personne.
        </div>
      )}

      {/* Everyone's running total */}
      <div className="card mb-3">
        <div className="card-body py-2">
          <h6 className="text-muted mb-2">Répartition</h6>
          {split.customers.map((c) => (
            <div key={c.id}
                 className={`d-flex justify-content-between ${c.id === meId ? "fw-bold" : ""}`}>
              <span>{c.display_name}{c.id === meId ? " (vous)" : ""}</span>
              <span>
                {c.total.toFixed(2)} €
                {c.due <= 0 && c.total > 0 && <span className="text-success ms-1">✓</span>}
              </span>
            </div>
          ))}
          <hr className="my-2" />
          <div className="d-flex justify-content-between text-muted">
            <span>Total table</span><span>{split.grand_total.toFixed(2)} €</span>
          </div>
        </div>
      </div>

      {/* My payment */}
      <div className="card">
        <div className="card-body text-center">
          <div className="text-muted">Votre part</div>
          <div className="display-6 fw-bold mb-2">{(me?.due ?? 0).toFixed(2)} €</div>
          {me && me.due <= 0 ? (
            <div className="text-success">Vous êtes à jour ✓</div>
          ) : (
            <button className="btn btn-he btn-lg w-100" disabled={busy || !me || me.due <= 0}
                    onClick={pay}>
              Payer {(me?.due ?? 0).toFixed(2)} €
            </button>
          )}
        </div>
      </div>
    </Shell>
  );
}

function Shell({ children }) {
  return <div className="guest-shell">{children}</div>;
}

function Header({ table, company }) {
  return (
    <div className="text-center mb-3">
      <h1 className="he-brand" style={{ color: "var(--he-dark)" }}>
        Handle<span style={{ color: "var(--he-primary)" }}>Easy</span>
      </h1>
      <div className="text-muted">{company?.name}</div>
      <h5 className="mt-1">Table {table?.table_number}</h5>
    </div>
  );
}
