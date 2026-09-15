# Manual Hostinger deploy (File Manager)

Upload the production frontend so `/beta` works on your live site.

## What to upload

Use **`agib-hostinger-deploy.zip`** (built from this branch).

It contains the contents of `dist/`:

- `index.html`
- `.htaccess` (required for `/beta` and other SPA routes)
- `assets/…`

## Steps in Hostinger File Manager

1. Open **hPanel** → **Websites** → **agarwalglobalinvestments.com** (or your domain) → **File Manager**.
2. Go to **`public_html`** (document root).
3. **Backup first** (important):
   - Select current files → **Compress** → download a backup zip, **or**
   - Rename `public_html` contents into a folder like `backup-YYYYMMDD`.
4. Upload **`agib-hostinger-deploy.zip`** into `public_html`.
5. Select the zip → **Extract**.
6. Confirm these exist directly under `public_html` (not nested in another folder):
   - `public_html/index.html`
   - `public_html/.htaccess`
   - `public_html/assets/`
7. Delete the uploaded zip from `public_html` after extract (optional cleanup).
8. Visit:
   - `https://YOUR-DOMAIN/`
   - `https://YOUR-DOMAIN/beta`
   - `https://YOUR-DOMAIN/beta/companies/RELIANCE`

## If `/beta` shows 404

`.htaccess` is missing or Apache rewrite is off.

1. Confirm `public_html/.htaccess` exists and includes:

```apache
RewriteEngine On
RewriteBase /
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^ index.html [L]
```

2. In Hostinger, ensure the site uses **Apache** (not Nginx-only without fallback rules).

## Important notes

- This zip is the **frontend only**. Node/API and the Python intelligence engine are **not** inside File Manager.
- Market/CMS features need your existing backend (`VITE_API_URL` / Render) and Supabase keys. If those were baked into your previous Hostinger build, rebuild with the same env secrets for full data.
- Do **not** upload `src/`, `server/`, `node_modules/`, or `intelligence-engine/` to `public_html`.

## Rebuild yourself later

```bash
git checkout cursor/agi-story-beta-4cc0
npm install
npm run build
# then zip dist/ contents and upload
cd dist && zip -r ../agib-hostinger-deploy.zip .
```
