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
- 2026-06: Applied user zip #4 (room-alerts): (a) OpenCV+OCR automatic stall detection from an uploaded venue layout (utils/layout_detect.py; deps numpy/opencv-python-headless/pytesseract/rapidocr-onnxruntime; tesseract binary optional, rapidocr pip fallback); (b) zoomable/pannable maps (ZoomableMap) on exhibitor reg, /stalls, admin placement + confirm dialog; (c) drag stalls onto map; (d) admin stat card "Approved Exhibitors" + pending/total sub-line (stats: approvedExhibitorCount/pendingExhibitorCount); (e) instant organizer email alerts on new exhibitor/visitor/enquiry (utils/notify.py, env ORGANIZER_NOTIFY_EMAILS/ADMIN_ALERTS); (f) enquiry auto-reply (ackSent/ackError). Re-merged object storage into exhibitors.py + admin.py (incl. detect-layout reading map back from object storage via get_object); re-applied WhatsApp CSS + hero centering the zip reverted. Aligned .env URLs to code-fetch-43 host.
- 2026-06: Testing agent iteration_5: backend 43/43, frontend 100%. Deployment readiness re-check: PASS. Note: tesseract is a non-persistent system binary; rapidocr-onnxruntime (in requirements.txt) is the deployment OCR fallback.

- 2026-06: FULL codebase replacement from user zip (roar-expo-full-emergent). Disk storage served via /api/uploads (frontend builds file links through api.fileUrl = VITE_API_BASE_URL + /uploads/...). Bundled coloured venue artwork + 141 stalls auto-published on startup (seed/final_layout). Exhibitor form: live per-field validation + 15-min stall reserve popup/countdown (POST /api/public/stalls/{n}/hold + release-hold with holdToken). Admin Approve/Reject/Reopen + record pages. Preserved .env; set Vite port 3000/allowedHosts; installed html5-qrcode; cleared old stalls/maps; fixed duplicate-CTA navbar inline style.
- 2026-06: Testing iteration_7: backend 7/7, frontend 100% — /stalls renders artwork (naturalWidth 3200) with 141 pins; reserve popup + validation + admin lifecycle verified. Deployment scan: no hard blockers (warn: version-gated bundled-layout auto-publish by design; disk uploads are ephemeral for user logos/ID cards — map self-heals). Note: this build does NOT use object storage and does NOT mount the floating WhatsApp button (not in user's zip).

- 2026-06: Deploy-readiness fixes on the full-codebase build: moved ALL uploads (venue map, logos, product images, ID cards) from pod disk to Emergent object storage (utils/storage), served via GET /api/uploads/{path} & /uploads/{path} (URL scheme unchanged); seed/final_layout.publish_image + id_card_image now use object storage; removed StaticFiles mounts + legacy stall_map_seed.py. Made startup non-destructive (ensure_final_layout → apply_final_layout(replace_unplaced=False)): auto-publishes map + 141 stalls, never deletes existing stalls. deployment_agent: PASS (no blockers). Verified map, exhibitor logo, and visitor ID-card email all work via object storage.

- 2026-06: Applied map-v2: new venue artwork (2918×1214) + 143-stall layout (published to object storage; kept my object-storage final_layout.py/server.py, copied only data + event_config + StallsPanel/StallRegistration). Fixed small-screen map FLICKER: ResizeObserver measured scroller clientWidth while the vertical scrollbar toggled → measure loop; fix = CSS scrollbar-gutter:stable on .zoom-map-scroller + <2px jitter guard in ZoomableMap.jsx. Also renamed public /stall-directory field _id→id (no ObjectId leak). Testing iteration_8: backend 100%, frontend 100% — 0.00px jitter on 390×844/768×1024/exhibitor-Ruby; 143 pins render.

- 2026-06: FIXED v2 map pin misalignment (user report: pins sat below their boxes). Root cause: final_layout_boxes.json was STALE for the current final-layout.png — its box heights were inflated so box-centers (y+h/2) landed at the box BOTTOM/aisle. Re-derived true box centers per column via a capped colored-band scan (HSV S>55,V>90; cap 52px to avoid merging stacked rows) and measured the 7 right-column boxes (XY1,Y25-Y29,XY2) individually via border runs. Kept mapX unchanged (columns were correct); rewrote all 143 mapY in seed/final_layout.json, bumped version to 2026-09-17-aligned2, re-applied with `python -m seed.final_layout_seed --keep-old` (143 refreshed, no bookings touched). Verified pixel-accurate via overlay + live /stalls screenshot. mapX/mapY are still image-percent + CSS translate(-50%,-50%); if artwork changes again, re-run the band-scan (see /tmp scripts approach) rather than trusting boxes.json.

- 2026-06 (correction): The v2 pin misalignment was NOT just a Y issue — the deployed seed/final_layout.json had stale X AND Y. User's uploaded zip `roar-expo-changes-final-map-v2.zip` (same final-layout.png, identical MD5) shipped the exact-aligned coordinates. FIX: copied the zip's final_layout.json + final_layout_boxes.json into /app/backend/seed/ (kept my object-storage final_layout.py & server.py — did NOT overwrite them per the zip-merge warning), bumped version to 2026-09-17-zipexact, re-applied via `python -m seed.final_layout_seed --keep-old` (143 refreshed, no bookings touched). Verified: live marker % equals zip values (B1 31.11/29.17, Y1 31.95/7.05) and every pill sits centered on its box. TAKEAWAY: when the user provides an aligned data file, adopt it directly instead of re-deriving coordinates.

- 2026-06: Swapped Ruby<->Regular category assignment per user (map: L=Ruby, Y=Regular). Changed packageCode on all Y* stalls ruby->regular and all L* stalls regular->ruby in seed/final_layout.json (+series), and swapped stallCount in config/event_config.py (ruby 71->27, regular 27->71; rates/labels unchanged). Re-seeded (143 refreshed). Verified via /api/public/config + /api/public/stall-directory: ruby=L(27), regular=Y(71). Frontend filters/picker read config dynamically, no FE code change.

- 2026-06: Fixed home hero ROAR logo off-center (shifted ~66px left). Cause: .hero-logo is display:block (global img reset) with margin:0, so parent text-align:center had no effect -> left-aligned in the 772px content box. Fix: added `margin: 0 auto` to .hero-logo in global.css. Verified logo center == hero-inner center on desktop (960) and mobile 390 (195). Other home sections (feature cards, Rose/Orange/Tiger, category grid) confirmed aligned.

- 2026-06: Fixed two exhibitor bugs. (1) Team alert email showed blank Mobile: utils/email_templates.exhibitor_alert_html used exhibitor.get('mobile') but the model field is 'phone' -> changed to 'phone'. (2) Admin exhibitors table hid the Stall column: 12-col table (min-width 720) overflowed and the sticky right Actions column (up to 6 buttons) pushed Stall/Status/etc out of view. Moved the Stall column to position 3 (right after Company) in AdminDashboard.jsx so the selected stall number is always visible. Editing/changing the stall already works via ExhibitorEditModal (Stall Number picker) + PATCH /admin/exhibitors/{id} reassignment logic (releases old stall, claims new). Verified end-to-end: registered exhibitor with stall B1 -> list shows B1, edit modal shows picker "B1 — current" + Mobile 9876543210; alert email renders phone.

- 2026-06: Fixed stall RATE not following the Ruby<->Regular swap. Root cause: seed/final_layout.apply_final_layout's update $set refreshed packageCode/size/mapX/mapY but NOT rate, so swapped stalls kept old rates (booking amount + /stalls hover tooltip + picker all read stall.rate). Fix: added `rate: pkg.rate` to the update $set and re-ran seed. Verified: Ruby(L)=24000, Regular(Y)=53000 via /api/public/stalls and a live booking (L1 -> stallRate 24000).
- 2026-06: Added stall SIZE display per user. Added `size` (e.g. 4m×3m) to each numbered package in config/event_config.py. Register page (StallRegistration.jsx rate-card): new "Size" column. Admin exhibitors table (AdminDashboard.jsx): new "Size" column (reads r.stallSize fallback to pkgSize map fetched from /public/config by packageCode). Verified both render & align correctly.
