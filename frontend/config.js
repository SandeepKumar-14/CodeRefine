/* ──────────────────────────────────────────────────────────────
   Coderefine — config.js  (production config, committed to git)
   ──────────────────────────────────────────────────────────────
   This file is loaded by all HTML pages and provides the
   production API URL and Supabase credentials.

   LOCAL DEVELOPMENT:
     config.local.js (gitignored) is loaded AFTER this file on
     app.html and auth.html, so its values override these for
     local dev. You do NOT need to edit this file locally.

   PRODUCTION (Vercel):
     config.local.js does not exist on Vercel, so these values
     are used directly.

   AFTER DEPLOYING YOUR RENDER BACKEND:
     Replace the placeholder below with your actual Render URL.
   ────────────────────────────────────────────────────────────── */

window.CODEREFINE_CONFIG = {
  API_BASE: "https://coderefine-vs4r.onrender.com",
  SUPABASE_URL: "https://mchcrkbefnfbyydowwkc.supabase.co",
  SUPABASE_ANON_KEY: "sb_publishable_s78PkUIb1q7xoB_AODibtQ_LYI7BMSe"
};
