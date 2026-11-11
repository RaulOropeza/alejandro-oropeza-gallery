/**
 * ============================================================================
 * ALEJANDRO OROPEZA — REUSABLE UI COMPONENT LIBRARY (src/components/ui.js)
 * All pages (Gallery, Showcase, About Me, Design System) are built strictly
 * from these components so any change here or in design-system.css cascades
 * automatically to every instance across the website.
 * ============================================================================
 */

export const Icons = {
  arrowLeft: `<svg class="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>`,
  arrowRight: `<svg class="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`,
  externalLink: `<svg class="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>`,
  instagram: `<svg class="w-3.5 h-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg>`,
  fiveHundredPx: `<svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="currentColor"><text x="12" y="15.2" text-anchor="middle" font-family="'Avenir', 'Helvetica Neue', Arial, sans-serif" font-weight="700" font-size="8.2" letter-spacing="-0.3">500</text></svg>`
};

/**
 * Heading Component (H1, H2, H3 — Non-Bold Futura)
 */
export function Heading({ level = 1, text, className = '', id = '' }) {
  const tag = `h${level}`;
  const dsClass = level === 1 ? 'ds-h1' : (level === 2 ? 'ds-h2' : 'ds-h3');
  const idAttr = id ? `id="${id}"` : '';
  return `<${tag} ${idAttr} class="${dsClass} ${className}">${text}</${tag}>`;
}

/**
 * Text Component (brand, body, label, value — Avenir)
 */
export function Text({ variant = 'body', tag = 'p', text, className = '', id = '' }) {
  const map = {
    brand: 'ds-brand-name',
    body: 'ds-body',
    label: 'ds-label',
    value: 'ds-value'
  };
  const dsClass = map[variant] || 'ds-body';
  const idAttr = id ? `id="${id}"` : '';
  return `<${tag} ${idAttr} class="${dsClass} ${className}">${text}</${tag}>`;
}

/**
 * Unified Button Component
 * Variants:
 *   - 'filled'   (Primary: recommended for primary actions)
 *   - 'outlined' (Secondary: recommended for secondary actions)
 *   - 'surface'  (Surface: recommended for navigation & other tools)
 */
export function Button({
  variant = 'filled',
  label = '',
  icon = '',
  iconPosition = 'left',
  onClick = '',
  title = '',
  className = '',
  id = ''
}) {
  const variantMap = {
    filled: 'ds-btn-filled',
    primary: 'ds-btn-filled',
    outlined: 'ds-btn-outlined',
    secondary: 'ds-btn-outlined',
    surface: 'ds-btn-surface'
  };
  const vClass = variantMap[variant] || 'ds-btn-filled';
  const isIconOnly = Boolean(icon && !label);
  const iconOnlyClass = isIconOnly ? 'ds-btn-icon' : '';
  const idAttr = id ? `id="${id}"` : '';
  const clickAttr = onClick ? `onclick="${onClick}"` : '';
  const titleAttr = title ? `title="${title}"` : '';

  let innerHtml = '';
  if (isIconOnly) {
    innerHtml = icon;
  } else if (icon && iconPosition === 'right') {
    innerHtml = `<span>${label}</span>${icon}`;
  } else if (icon) {
    innerHtml = `${icon}<span>${label}</span>`;
  } else {
    innerHtml = `<span>${label}</span>`;
  }

  return `<button ${idAttr} ${clickAttr} ${titleAttr} class="ds-btn ${vClass} ${iconOnlyClass} ${className} focus:outline-none">${innerHtml}</button>`;
}

/**
 * Social Media Circular Pill Button (Instagram & 500px)
 */
export function SocialPill({ href = '#', title = '', icon = '', className = '' }) {
  return `<a href="${href}" target="_blank" rel="noopener noreferrer" title="${title}" class="ds-social-pill ${className} focus:outline-none">${icon}</a>`;
}

/**
 * SpecTable Component (Hairline key-value rows for EXIF & Metadata)
 */
export function SpecTable({ rows = [], className = '' }) {
  const rowsHtml = rows.map(r => `
    <div class="ds-spec-row">
      <span class="ds-label">${r.label}</span>
      <span ${r.valueId ? `id="${r.valueId}"` : ''} class="ds-value">${r.value}</span>
    </div>
  `).join('');
  return `<div class="${className}">${rowsHtml}</div>`;
}

/**
 * ThumbnailCard Component (No copyright tag, 1.03x hover zoom)
 */
export function ThumbnailCard({ photo, index, heightClass = 'h-48 sm:h-52', flexStyle = '' }) {
  const styleAttr = flexStyle ? `style="${flexStyle}"` : '';
  return `
    <div id="thumb-card-${photo.id}" onclick="window.appOpenPhoto(${index})" ${styleAttr} class="ds-thumb-card ${heightClass}">
      <img src="${photo.src}" alt="${photo.title}" loading="lazy" />
    </div>
  `;
}
