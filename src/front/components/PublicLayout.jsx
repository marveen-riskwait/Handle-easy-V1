// Public chrome for the visitor-facing site (catalogue, bike detail…).
import { Link, Outlet } from "react-router-dom";

export function PublicLayout() {
  return (
    <div className="rdv-site">
      <header className="rdv-header">
        <div className="container d-flex align-items-center justify-content-between py-2">
          <Link to="/" className="rdv-brand">RDV<span>Cycles</span></Link>
          <nav className="d-flex align-items-center gap-3">
            <Link to="/" className="rdv-nav-link">Catalogue</Link>
            <Link to="/login" className="btn btn-outline-light btn-sm">Espace équipe</Link>
          </nav>
        </div>
      </header>

      <main><Outlet /></main>

      <footer className="rdv-footer">
        <div className="container py-4 d-flex flex-wrap justify-content-between gap-3">
          <div>
            <div className="rdv-brand rdv-brand--sm">RDV<span>Cycles</span></div>
            <p className="mb-0 small text-white-50">
              Location de vélo au lac du Salagou.
            </p>
          </div>
          <div className="small text-white-50">
            © {new Date().getFullYear()} RDV Cycles — Le Bosc (34)
          </div>
        </div>
      </footer>
    </div>
  );
}
