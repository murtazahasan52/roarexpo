# ROAR Expo — PRD

## Source
Imported from GitHub: https://github.com/murtazahasan52/roarexpo.git (main).
The repo shipped as git bundles; extracted the FastAPI + React (Vite) app.

## Task
User request: "Fix bugs / issues" on this codebase.

## Architecture (as wired into Emergent env)
- Backend: FastAPI (`/app/backend`, from repo's `backend_fastapi/`), supervisor `uvicorn server:app` on :8001, all routes under `/api`.
- Frontend: React + Vite (`/app/frontend`), supervisor `yarn start` → `vite --port 3000 --host 0.0.0.0`.
- DB: MongoDB local (`MONGO_URL`, `DB_NAME=roar_expo`).
- Frontend calls backend via `VITE_API_BASE_URL = <REACT_APP_BACKEND_URL>/api`.
- Vite config: `allowedHosts: true`, HMR clientPort 443/wss for the preview proxy.

## App overview
Event registration system for ROAR Saifee Burhani Business Expo (Nagpur, Jan 2027):
- Public marketing site, exhibitor (stall) registration with map-based stall picker, visitor registration with QR ID card, admin dashboard (approvals, stalls/map, CSV export, check-in, admins/permissions).
- Two backends exist in repo (Node `backend/`, FastAPI `backend_fastapi/`); we run FastAPI.

## Setup done (2026-06)
- Copied `backend_fastapi/` → `/app/backend`, `frontend/` → `/app/frontend`.
- Installed backend requirements into `/root/.venv`, frontend deps via yarn.
- Created `.env` files; added Vite `start` script + proxy-friendly config.
- Seeded admin, 103 sample stalls, sample stall map.
- Verified: health, public config/stalls, admin login, visitor + exhibitor registration all work (email non-blocking since SMTP unset).

## Notes / placeholders
- SMTP (SMTP_USER/SMTP_PASS) unset → confirmation emails will not send but flows succeed. WhatsApp disabled.

## Backlog / Next
- Awaiting user to specify concrete bugs/issues to fix.

## Change log
- 2026-06: Fixed duplicate navbar CTAs (mobile-only "Exhibit"/"Visit" were showing on desktop) — verified (iteration_1).
- 2026-06: Migrated all file uploads (exhibitor logos, product images, admin stall-map, visitor ID-card PNG) from pod-local disk to Emergent object storage (utils/storage.py; served via GET /api/files/{path}). Re-seeded sample stall map into object storage. Resolves the deploy blocker.
- 2026-06: Configured Gmail SMTP (mkt@roarexpo.com). NOTE: the supplied password is a normal account password which Gmail REJECTS (535 BadCredentials) — real email DELIVERY requires a 16-char Gmail App Password. Registration is non-blocking so forms still succeed.
- 2026-06: Verified visitor + exhibitor registration end-to-end (iteration_2: backend 12/12, frontend visitor E2E). Email send confirmed non-blocking.
- 2026-06: Fixed hero ROAR logo centering (display:block + auto margins) — verified 0px offset (iteration_3).
- 2026-06: Added floating WhatsApp button on all public pages linking to wa.me/919284182675 — verified (iteration_3).
- 2026-06: EMAIL NOW WORKING — Gmail App Password for mkt@roarexpo.com accepted (SMTP login OK, test email delivered). Verified live visitor (QR ID card) + exhibitor (confirmation) registrations send email with no emailError. roarexpo.com confirmed on Google Workspace (MX=google).
- 2026-06: Applied user zip #1 (rebrand): navbar + hero now "Business Expo – Nagpur" + new "Managed by Dawoodi Bohra Department of Economic Affairs" line (.hero-managed-by).
- 2026-06: Removed duplicate "Enquiry" nav link (kept the Enquiry button).
- 2026-06: Applied large user zip #2 (features): Enquiry system (public /enquiry + admin EnquiriesPanel), EntranceQRPanel, AdminsPanel, economic-affairs branding.
- 2026-06: Applied user zip #3 (features): PDF stall-map upload (pypdfium2 4.30.0 → PNG), series→category mapping (map-series), generate-stalls-from-series, public /stalls directory page (StallDirectory) + /api/public/stall-directory, admin edit/delete for visitors + exhibitors + enquiries (releases held stalls on exhibitor delete). Re-merged Emergent object storage into upload.py (save_upload/read_upload/write_upload_bytes → /api/files URLs) + admin stall-map handler; re-applied WhatsApp CSS, hero logo centering, and Navbar inline-style CTA fix that the zips reverted.
- 2026-06: Testing agent iteration_4: backend 33/33, frontend 100% acceptance. Deployment readiness: PASS (deployment_agent, no blockers). Ready for the platform Deploy button.
