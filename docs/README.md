# Alejandro Oropeza — Production Distribution

This directory (`dist/`) contains the complete, self-contained production build ready for 1-click deployment.

- **Initial HTML size:** ~38 KB (loads instantly)
- **Images:** Full-resolution JPEGs in `photos/` (6000×4000 cover masters) + crisp 1600px Lanczos gallery thumbnails in `photos/thumbs/`
- **Routing:** Client-side hash routing (`#/photo/:id`, `#/about`, `#/gallery`) with full browser Back/Forward support
- **Social Metadata:** Open Graph, Twitter cards, and SVG favicon pre-configured
- **Hosting:** 100% static — zero servers or databases required (100% free hosting)

## Publishing Options

### Option A: Cloudflare Pages (Recommended)
1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/) > **Workers & Pages** > **Create application** > **Pages**.
2. Connect your GitHub repository (or choose **Direct Upload** and drag the entire `dist` folder).
3. If connecting GitHub:
   - **Build command:** `python3 scripts/manage_gallery.py build`
   - **Build output directory:** `dist`
4. Click **Deploy**. Your site is live on `https://<project>.pages.dev` with free global CDN and SSL.
5. In **Custom domains**, add `alejandrooropeza.com` with automatic HTTPS.

### Option B: Vercel
1. Log in to [Vercel](https://vercel.com/) and click **Add New Project**.
2. Import your GitHub repository.
3. Set **Output Directory** to `dist`.
4. Click **Deploy**.

### Option C: Netlify
1. Log in to [Netlify](https://www.netlify.com/).
2. Drag and drop the `dist/` folder for instant deployment, or connect GitHub with publish directory set to `dist`.

### Option D: GitHub Pages
1. In your GitHub repository, go to **Settings** > **Pages**.
2. Under **Build and deployment**, select **Deploy from a branch**.
3. Choose your branch and set the folder to `/dist` (or `/` if deploying from a `gh-pages` branch).
