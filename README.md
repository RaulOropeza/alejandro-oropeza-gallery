# Alejandro Oropeza — Photo Gallery & Design System

A modular photography portfolio and living Design System built around pure monochrome tokens, **Futura (non-bold)** display headings, and **Avenir** body/metadata typography.

## Project Structure

- [`src/styles/design-system.css`](./src/styles/design-system.css) — **Single Source of Truth** for all CSS custom properties (colors, frosted-glass blur, font families, button heights, spacing, motion curves) and semantic component classes (`.ds-h1`, `.ds-h2`, `.ds-h3`, `.ds-brand-name`, `.ds-body`, `.ds-label`, `.ds-value`, `.ds-btn`, `.ds-nav-btn`, `.ds-floating-header`, `.ds-thumb-card`, `.ds-spec-row`).
- [`src/components/ui.js`](./src/components/ui.js) — Reusable JavaScript UI component library (`Heading`, `Text`, `Button`, `NavButton`, `SpecTable`, `ThumbnailCard`).
- [`src/data/photos.json`](./src/data/photos.json) — Structured content catalog for site copy, all photographs, technical EXIF metadata (`focalLength`, `aperture`, `shutterSpeed`, `iso`), and third-party print shop hooks.
- [`scripts/manage_gallery.py`](./scripts/manage_gallery.py) — CLI tool that automatically extracts EXIF metadata and aspect ratios from new `.jpg` files, updates `photos.json`, and builds `index.html`.
- [`public/photos/`](./public/photos/) — Original high-resolution photographs.

---

## Common Workflows

### 1. Adding a New Photograph (with Auto-EXIF Extraction)
Drop your `.jpg` file in the workspace (or tell the AI assistant in chat) and run:
```bash
python3 scripts/manage_gallery.py add /path/to/MyPhoto.jpg \
  --title "Title of Photograph" \
  --location "City, Country · 2026" \
  --description "Story behind the photograph." \
  --row 3
```

### 2. Updating the Design System (Cascading Changes)
Edit any variable in `:root` or any `.ds-*` class inside [`src/styles/design-system.css`](./src/styles/design-system.css), then run:
```bash
python3 scripts/manage_gallery.py build
```
All pages (`Gallery`, `Showcase`, `About me`, and `/design-system`) will update automatically.

### 3. Enabling Third-Party Print Sales
In [`src/data/photos.json`](./src/data/photos.json), set `"printShopGlobalEnabled": true` (or set `"enabled": true` on individual photos under `"print"`) and provide your third-party checkout link (`providerUrl` for Shopify, Printful, Gelato, or Stripe).

### 4. Deploying & Connecting Your Custom Domain
1. Push this directory to a GitHub repository.
2. Import the repository into **Cloudflare Pages**, **Vercel**, or **Netlify** (Output directory: `.`).
3. In your hosting dashboard under **Custom Domains**, add your domain (e.g., `alejandrooropeza.com`) and follow the 2 DNS records shown.
