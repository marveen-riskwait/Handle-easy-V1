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
  const [tipPct, setTipPct] = useState(0);        // 0 | 5 | 10 | 15
  const [receipt, setReceipt] = useState(null);   // last payment {amount, tip, total_charged}
  const [reviews, setReviews] = useState({});     // { itemId: {rating, comment, done} }

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

  const pay = async (tip) => {
    setBusy(true); setError("");
    try {
      const { data: res } = await api.post(`/sessions/${data.session.id}/pay`,
        { customer_id: meId, tip: tip || 0 });
      setReceipt(res.payment);
      setData((d) => ({ ...d, split: res.split, session: res.session }));
    } catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };

  const submitReview = async (item) => {
    const r = reviews[item.id] || {};
    if (!r.rating) return;
    setBusy(true);
    try {
      await api.post("/reviews", {
        customer_id: meId,
        product_id: item.product_id,
        rating: r.rating,
        comment: r.comment || "",
      });
      setReviews((prev) => ({ ...prev, [item.id]: { ...r, done: true } }));
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
      <PaymentCard me={me} tipPct={tipPct} setTipPct={setTipPct} pay={pay}
                   busy={busy} receipt={receipt} />

      {/* Rate the dishes I had — shown once I've paid my share */}
      {me && me.paid > 0 && (
        <ReviewsCard
          items={split.items.filter((it) => it.assignee_ids.includes(meId) && it.product_id)}
          reviews={reviews} setReviews={setReviews}
          submitReview={submitReview} busy={busy} />
      )}
    </Shell>
  );
}

function PaymentCard({ me, tipPct, setTipPct, pay, busy, receipt }) {
  const due = me?.due ?? 0;
  const tip = Math.round(due * (tipPct / 100) * 100) / 100;
  const total = Math.round((due + tip) * 100) / 100;

  if (me && due <= 0) {
    return (
      <div className="card">
        <div className="card-body text-center">
          <div className="display-6">✓</div>
          <div className="text-success fw-semibold">Vous êtes à jour</div>
          {receipt && (
            <div className="small text-muted mt-2">
              Payé {receipt.total_charged.toFixed(2)} €
              {receipt.tip > 0 && ` (dont ${receipt.tip.toFixed(2)} € de pourboire)`}
              <br />Reçu #{receipt.stripe_payment_id}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-body text-center">
        <div className="text-muted">Votre part</div>
        <div className="display-6 fw-bold mb-1">{due.toFixed(2)} €</div>

        <div className="text-muted small mb-1">Ajouter un pourboire ?</div>
        <div className="btn-group mb-3" role="group">
          {[0, 5, 10, 15].map((p) => (
            <button key={p} type="button"
                    className={`btn btn-sm ${tipPct === p ? "btn-he" : "btn-outline-secondary"}`}
                    onClick={() => setTipPct(p)}>
              {p === 0 ? "Aucun" : `${p}%`}
            </button>
          ))}
        </div>

        {tip > 0 && (
          <div className="small text-muted mb-2">
            Part {due.toFixed(2)} € + pourboire {tip.toFixed(2)} €
          </div>
        )}

        <button className="btn btn-he btn-lg w-100" disabled={busy || !me || due <= 0}
                onClick={() => pay(tip)}>
          Payer {total.toFixed(2)} €
        </button>
      </div>
    </div>
  );
}

function StarRating({ value, onChange }) {
  return (
    <div style={{ fontSize: "1.4rem", lineHeight: 1, cursor: "pointer" }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span key={n} onClick={() => onChange(n)}
              style={{ color: n <= value ? "var(--he-primary)" : "#ccc" }}>★</span>
      ))}
    </div>
  );
}

function ReviewsCard({ items, reviews, setReviews, submitReview, busy }) {
  if (!items.length) return null;
  const set = (id, patch) =>
    setReviews((prev) => ({ ...prev, [id]: { ...(prev[id] || {}), ...patch } }));

  return (
    <div className="card mt-3">
      <div className="card-body">
        <h6 className="text-muted mb-2">Notez vos plats</h6>
        {items.map((it) => {
          const r = reviews[it.id] || {};
          return (
            <div key={it.id} className="mb-3 pb-2 border-bottom">
              <div className="fw-semibold">{it.name}</div>
              {r.done ? (
                <div className="text-success small">Merci pour votre note ✓</div>
              ) : (
                <>
                  <StarRating value={r.rating || 0} onChange={(n) => set(it.id, { rating: n })} />
                  <input className="form-control form-control-sm my-2"
                         placeholder="Commentaire (optionnel)"
                         value={r.comment || ""} onChange={(e) => set(it.id, { comment: e.target.value })} />
                  <button className="btn btn-sm btn-outline-secondary"
                          disabled={busy || !r.rating} onClick={() => submitReview(it)}>
                    Envoyer
                  </button>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
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
