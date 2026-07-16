# Audit — RDV Cycles (Lot 0)

Revue de la base de code au commit `5d9c3ef` (branche `claude/rdv-cycles-base`).
Portée : back-end Flask (`src/api`, `src/app.py`), configuration, migration,
front-end SPA (`src/front`), outillage (`scripts`, Docker, CI).

Le back-end « Lot 0 — Fondations » est propre et bien pensé : argent en centimes
entiers, dates UTC *aware*, JWT en cookie httpOnly + CSRF double-submit, rotation
des refresh tokens avec blocklist, modèle de données cohérent avec la migration
initiale. Les points ci-dessous sont classés par gravité. Ceux marqués
**✅ Corrigé** l'ont été dans cette branche (`claude/bike-rental-audit-17hkme`) ;
les autres sont documentés avec une recommandation.

| # | Gravité | Sujet | État |
|---|---------|-------|------|
| C1 | 🔴 Critique | Flask-Admin exposé sans authentification | ✅ Corrigé |
| C2 | 🔴 Critique | Secret JWT par défaut/faible, sans garde-fou en prod | ✅ Corrigé |
| H1 | 🟠 Élevé | Le front-end est encore l'app resto « Handle Easy » | 📋 Documenté |
| H2 | 🟠 Élevé | Smoke test `verify_flow.py` pointe la mauvaise app | ✅ Corrigé |
| H3 | 🟠 Élevé | `.env.example` casse le flux cookie/CSRF en Codespaces | ✅ Corrigé |
| M1 | 🟡 Moyen | Champs Register front/back désalignés (noms perdus) | 📋 Documenté |
| M2 | 🟡 Moyen | Aucune limitation de débit sur login/register | 📋 Documenté |
| M3 | 🟡 Moyen | `token_blocklist` grossit sans purge | 📋 Documenté |
| M4 | 🟡 Moyen | Repli SQLite `/tmp` — données volatiles | 📋 Documenté |
| M5 | 🟡 Moyen | CORS autorise localhost même en production | 📋 Documenté |
| L1 | 🔵 Faible | Aucun test automatisé, aucune CI | 📋 Documenté |
| L2 | 🔵 Faible | Passerelle de paiement : euros (float) vs centimes | 📋 Documenté |
| L3 | 🔵 Faible | `Reservation.reference` sans générateur | 📋 Documenté |

---

## 🔴 Critiques

### C1 — Flask-Admin exposé sans authentification ✅ Corrigé
`src/api/admin.py` monte une `ModelView` sur **chaque** table (`User`,
`Payment`, `Reservation`, …) sans aucun contrôle d'accès. `/admin` permettait
donc à quiconque d'atteindre l'URL de lire et modifier tous les comptes, les
paiements et les réservations.

**Correctif** : `src/app.py` ne monte plus l'admin qu'en développement
(`FLASK_DEBUG=1`) ou si `ENABLE_ADMIN=1` est explicitement posé (typiquement
derrière un proxy d'auth réseau). La commodité en dev est préservée, le trou en
prod est fermé.
**Suite recommandée** : si un back-office admin est voulu en prod, protéger les
vues Flask-Admin par une vraie auth (rôle `admin`) plutôt que de se reposer sur
le drapeau.

### C2 — Secret JWT par défaut/faible sans garde-fou ✅ Corrigé
`JWT_SECRET_KEY` retombait sur `"super-secret-change-me"` (22 octets — sous le
minimum de 32 recommandé pour HMAC-SHA256, cf. `InsecureKeyLengthWarning` au
démarrage). Avec ce secret, n'importe qui peut **forger un JWT admin**.

**Correctif** : garde *fail-closed* dans `src/app.py` — en production, le
démarrage échoue si `FLASK_APP_KEY` vaut le défaut **ou** fait moins de 32
caractères. En dev, comportement inchangé.

---

## 🟠 Élevés

### H1 — Le front-end est encore l'application restaurant 📋
Le back-end est RDV Cycles (location de vélo) mais **tout `src/front` est resté
l'ancienne app « Handle Easy »** (partage d'addition au restaurant) :
- `pages/Login.jsx` / `Register.jsx` : « Espace restaurateur », « Créer un
  restaurant » ;
- `routes.jsx` : `/table/:token`, `GuestTable`, `TableDetail`, `Dashboard` ;
- `store.js` : commentaire « guest split flow ».

Aucun écran de catalogue / disponibilité / tunnel de réservation n'existe. Le
front et le back sont donc désynchronisés. **Non corrigé ici** : c'est une
réécriture complète du front (Lot 5 de la feuille de route), pas un patch
ponctuel. À planifier explicitement.

### H2 — Smoke test obsolète ✅ Corrigé
`scripts/verify_flow.py` testait les endpoints resto (`/tables`, `/sessions`,
`/table/<token>`) et se connectait à `admin@demo.com` (le seed crée
`admin@rdv-cycles.fr`). Il échouait donc dès la 2ᵉ requête et donnait une
fausse impression de couverture.

**Correctif** : réécrit pour l'API réelle — health + flux d'auth complet
(register → me → mot de passe faible rejeté → doublon rejeté → logout →
401, puis login admin seedé → rotation du refresh). **Vérifié : 9/9 OK** contre
un back-end lancé et seedé.

### H3 — `.env.example` casse les cookies en Codespaces ✅ Corrigé
`VITE_BACKEND_URL=http://localhost:3001` contredisait la stratégie *same-origin*
documentée dans `vite.config.js` et `services/api.js` (« garder VITE_BACKEND_URL
vide »). Renseigné, le navigateur appelle un hôte *cross-site* et le cookie
httpOnly `SameSite=Lax` + CSRF ne passe plus sous Codespaces/tunnels.

**Correctif** : la variable est remise à vide avec un commentaire expliquant
pourquoi. Le proxy Vite `/api → :3001` gère le dev en same-origin.

---

## 🟡 Moyens

### M1 — Champs Register désalignés 📋
`front/pages/Register.jsx` envoie `company_name`, `firstname`, `lastname` ;
`routes/auth.py::register` lit `first_name`, `last_name` et ignore
`company_name`. Les noms saisis sont donc **silencieusement perdus**. À traiter
dans la réécriture du front (H1) — corriger la page isolément n'a pas de sens
tant qu'elle affiche « Créer un restaurant ».

### M2 — Pas de limitation de débit 📋
`/auth/login` et `/auth/register` n'ont aucun *rate limiting* → force brute des
mots de passe et énumération de comptes possibles. Recommandation : `Flask-Limiter`
(p. ex. 5–10 tentatives/min/IP sur login).

### M3 — `token_blocklist` sans purge 📋
Chaque token révoqué (logout, rotation refresh) insère une ligne jamais
supprimée. Les access tokens expirent en 15 min mais leur `jti` reste
indéfiniment → la table enfle et le `token_in_blocklist_loader` (exécuté à
**chaque** requête authentifiée) ralentit. Recommandation : tâche de purge des
entrées plus vieilles que la TTL du token (`created_at`).

### M4 — Repli SQLite `/tmp` 📋
Sans `DATABASE_URL`, la base est `sqlite:////tmp/rdv_cycles.db` — volatile
(perdue au redémarrage) et dans un répertoire partagé. Parfait pour un dev
jetable, dangereux si ça devient silencieusement le stockage « prod ».
Recommandation : exiger `DATABASE_URL` quand `ENV != development`.

### M5 — CORS trop permissif en production 📋
`app.py` ajoute `http://localhost:3000` et `:5173` à la liste des origines
autorisées **dans tous les environnements**. Recommandation : n'autoriser que
`FRONTEND_URL` hors développement.

---

## 🔵 Faibles / Informationnels

### L1 — Aucun test automatisé ni CI 📋
Il n'existe que le script manuel `verify_flow.py`. Recommandation : suite
`pytest` (client de test Flask, base SQLite en mémoire) couvrant auth + modèles,
et un workflow GitHub Actions. Le back-end est déjà testable en l'état (usine
`app`, cf. l'import direct utilisé par la vérif de cette branche).

### L2 — Passerelle de paiement : unités 📋
`services/payment/gateway.py::charge(amount)` manipule des euros en `float`
alors que les modèles stockent des **centimes entiers**. À aligner lors du
câblage du paiement (Lot 4) pour éviter toute dérive d'arrondi.

### L3 — `Reservation.reference` sans générateur 📋
Le champ est `unique`, `not null` mais sans `default`. La future création de
réservation (Lot 3) devra fournir une référence (p. ex. `RDV-XXXXXX`).

### Info — Écart README ↔ code livré
Le README annonce « réservation + paiement en ligne » ; le back-end n'expose
pour l'instant que `/api/health` et `/api/auth/*` (`routes/__init__.py`
n'enregistre que `auth_bp`). C'est conforme au « Lot 0 » de la feuille de route,
mais l'écart mérite d'être explicite pour ne pas surprendre.

---

## Corrigé dans cette branche

- **C1** admin gated hors prod — `src/app.py`, `src/api/admin.py`
- **C2** garde-fou secret JWT en prod — `src/app.py`
- **H2** `scripts/verify_flow.py` réécrit pour l'API réelle (9/9 OK)
- **H3** `.env.example` : `VITE_BACKEND_URL` remis à vide + explication

## Prochaines étapes suggérées (par priorité)

1. **Réécrire le front-end** pour la location de vélo (H1, M1) — catalogue,
   disponibilité, tunnel de réservation, compte client.
2. **Durcir l'auth** : rate limiting (M2), purge blocklist (M3).
3. **Filet de sécurité** : suite `pytest` + CI (L1).
4. **Config prod** : exiger `DATABASE_URL` (M4), restreindre CORS (M5).
5. Poursuivre la feuille de route back-end : catalogue → disponibilité →
   réservation avec *hold* → paiement (aligner les unités, L2).
