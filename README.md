# RDV Cycles

Plateforme de **location de vélo** au lac du Salagou : catalogue, disponibilités
en temps réel, **réservation + paiement en ligne**, e-mail de confirmation, et
un back-office pour l'équipe. Pensée **mobile-first** et pour de la charge
(milliers de clients).

## Stack

- **Frontend :** React + React Router + Context API + Axios + Bootstrap 5.3 (Vite)
- **Backend :** Flask + Flask-JWT-Extended (**JWT en cookie httpOnly** + CSRF, access
  court + refresh rotatif révocable) + SQLAlchemy + Alembic (Flask-Migrate)
- **DB :** PostgreSQL (SQLite en repli pour le dev)
- **Paiement :** passerelle *Stripe-shaped*, mock d'abord

## Démarrer (sans Docker)

```bash
# 1. Config
cp .env.example .env

# 2. Backend (port 3001)
pipenv install          # ou: python -m venv .venv && pip install -r requirements.txt
pipenv run upgrade      # applique les migrations
pipenv run seed         # données de démo (stations, catalogue, tarifs, stock)
pipenv run start        # API sur http://localhost:3001

# 3. Frontend (autre terminal, port 3000)
npm install
npm run dev
```

Comptes de démo : **admin@rdv-cycles.fr / demo1234** (admin) et
**client@demo.com / demo1234** (client).

## Modèle de données (résumé)

`User` · `Station` · `BikeModel` (→ `price_category`) · `BikeUnit` (stock) ·
`RatePlan` (grille tarifaire) · `Option` · `Reservation` → `ReservationLine` /
`ReservationOption` · `Payment` · `Review` · `TokenBlocklist`.

- On réserve un **modèle + taille** ; l'**unité physique** est affectée au retrait.
- Les **montants sont en centimes** (entiers), les **dates en UTC**.
- Le prix vient de la **catégorie tarifaire** (5 colonnes de la grille), pas du
  modèle — plusieurs modèles peuvent partager un tarif.

## Tarification

Le moteur combine les forfaits de la grille (2 h, ½ j, 1→4 j) avec les tarifs
marginaux — **heure = 15 €**, **jour sup = +35 €** (électrique) / **+25 €**
(musculaire) — pour donner le **meilleur prix** sur n'importe quelle durée.

## Feuille de route

- **Lot 0 ✅** — fondations : nettoyage, modèles, auth (cookies httpOnly + refresh
  + blocklist), seed, migration initiale, back-office.
- **Lot 1** — catalogue public (stations, modèles, tarifs, options).
- **Lot 2** — disponibilité + devis (prix calculé côté serveur).
- **Lot 3** — réservation avec **hold** anti-surbooking.
- **Lot 4** — paiement + e-mail de confirmation.
- **Lot 5** — front mobile-first (tunnel de réservation, compte).
- **Phase 2** — avis, atelier, i18n (EN), itinéraires/GPX.
```
