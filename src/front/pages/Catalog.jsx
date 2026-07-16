// Public home: the RDV Cycles bike catalogue. Lists every active model with its
// "from" price, plus the pickup stations. Consumes the Lot 1 public endpoints.
import { useEffect, useState } from "react";

import { getBikes, getStations, euros } from "../services/catalog";

export function Catalog() {
  const [bikes, setBikes] = useState([]);
  const [stations, setStations] = useState([]);
  const [state, setState] = useState("loading"); // loading | ready | error

  useEffect(() => {
    Promise.all([getBikes(), getStations()])
      .then(([b, s]) => { setBikes(b); setStations(s); setState("ready"); })
      .catch(() => setState("error"));
  }, []);

  return (
    <>
      <section className="rdv-hero">
        <div className="container">
          <h1>Louez votre vélo au lac du Salagou</h1>
          <p className="lead">
            VTT électriques, VTC, vélos enfants et haut de gamme — réservez en
            ligne, récupérez en boutique.
          </p>
        </div>
      </section>

      <section className="container py-4">
        <h2 className="rdv-section-title">Notre catalogue</h2>

        {state === "loading" && <p className="text-muted">Chargement du catalogue…</p>}
        {state === "error" && (
          <div className="alert alert-warning">
            Impossible de charger le catalogue. Le back-end est-il démarré&nbsp;?
          </div>
        )}

        {state === "ready" && (
          <div className="row g-3">
            {bikes.map((b) => (
              <div className="col-12 col-sm-6 col-lg-4" key={b.id}>
                <article className="rdv-card h-100">
                  <div className="rdv-card__media">
                    {b.image_url
                      ? <img src={b.image_url} alt={b.name} />
                      : <div className="rdv-card__placeholder">🚲</div>}
                    {b.is_electric && <span className="rdv-badge">Électrique</span>}
                  </div>
                  <div className="rdv-card__body">
                    <h3>{b.name}</h3>
                    {b.description && <p className="rdv-card__desc">{b.description}</p>}
                    <div className="rdv-card__foot">
                      {b.from_price_cents != null && (
                        <span className="rdv-price">
                          dès <strong>{euros(b.from_price_cents)}</strong>
                        </span>
                      )}
                      <button className="btn btn-rdv btn-sm" disabled title="Bientôt disponible">
                        Réserver
                      </button>
                    </div>
                  </div>
                </article>
              </div>
            ))}
          </div>
        )}
      </section>

      {state === "ready" && stations.length > 0 && (
        <section className="rdv-stations">
          <div className="container py-4">
            <h2 className="rdv-section-title">Points de retrait</h2>
            <div className="row g-3">
              {stations.map((s) => (
                <div className="col-12 col-md-6" key={s.id}>
                  <div className="rdv-station">
                    <h3>
                      {s.name}
                      {s.is_seasonal && <span className="rdv-tag">Saisonnier</span>}
                    </h3>
                    <p className="mb-0 text-muted small">
                      {[s.address, s.postal_code, s.city].filter(Boolean).join(", ")}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </>
  );
}
