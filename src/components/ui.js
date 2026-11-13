/**
 * ============================================================================
 * ALEJANDRO OROPEZA — REUSABLE UI COMPONENT LIBRARY (src/components/ui.js)
 * All pages (Gallery, Showcase, About Me, Design System) are built strictly
 * from these components so any change here or in design-system.css cascades
 * automatically to every instance across the website.
 * ============================================================================
 */

export const Icons = {
  arrowLeft: `<svg width="20" height="20" class="shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>`,
  arrowRight: `<svg width="20" height="20" class="shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`,
  menu: `<svg width="20" height="20" class="shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/></svg>`,
  close: `<svg width="20" height="20" class="shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  fullscreen: `<svg width="20" height="20" class="shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>`,
  instagram: `<span class="ds-icon-glyph ds-icon-glyph-ig"></span>`,
  fiveHundredPx: `<span class="ds-icon-glyph ds-icon-glyph-500px"></span>`
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
 * Master Component 1: Button (.ds-btn) — Supports 'tonal' (default) and 'surface' variants
 * Responsive sizing:
 *   - Mobile (< 768px): 48px high, 12px horizontal padding
 *   - Desktop (>= 768px): 40px high, 16px horizontal padding
 */
export function Button({
  label = '',
  iconLeft = '',
  iconRight = '',
  variant = 'tonal',
  onClick = '',
  href = '',
  ariaLabel = '',
  className = '',
  id = ''
}) {
  const variantCls = variant === 'surface' ? 'ds-btn-surface' : '';
  const classes = ['ds-btn', variantCls, className, 'focus:outline-none'].filter(Boolean).join(' ');
  const idAttr = id ? `id="${id}"` : '';
  const ariaAttr = ariaLabel ? `aria-label="${ariaLabel}"` : '';
  const innerHtml = `${iconLeft}<span>${label}</span>${iconRight}`;

  if (href) {
    return `<a ${idAttr} href="${href}" target="_blank" rel="noopener noreferrer" ${ariaAttr} onmousemove="trackMenuLight(event, this)" class="${classes}">${innerHtml}</a>`;
  }
  const clickAttr = onClick ? `onclick="${onClick}"` : '';
  return `<button type="button" ${idAttr} ${clickAttr} ${ariaAttr} onmousemove="trackMenuLight(event, this)" class="${classes}">${innerHtml}</button>`;
}

/**
 * Surface Button (.ds-btn.ds-btn-surface) — Transparent by default; reveals Tonal background + animation on hover
 */
export function SurfaceButton(props = {}) {
  return Button({ ...props, variant: 'surface' });
}

/**
 * Master Component 2: Circular IconButton (.ds-icon-btn) — Supports 'tonal' (default) and 'surface' variants
 * Responsive sizing:
 *   - Mobile (< 768px): 48px × 48px circle
 *   - Desktop (>= 768px): 40px × 40px circle
 */
export function IconButton({
  icon = '',
  variant = 'tonal',
  onClick = '',
  href = '',
  title = '',
  ariaLabel = '',
  className = '',
  id = ''
}) {
  const variantCls = variant === 'surface' ? 'ds-btn-surface' : '';
  const classes = ['ds-icon-btn', variantCls, className, 'focus:outline-none'].filter(Boolean).join(' ');
  const idAttr = id ? `id="${id}"` : '';
  const titleAttr = title ? `title="${title}"` : '';
  const ariaAttr = ariaLabel ? `aria-label="${ariaLabel}"` : '';

  if (href) {
    return `<a ${idAttr} href="${href}" target="_blank" rel="noopener noreferrer" ${titleAttr} ${ariaAttr} onmousemove="trackMenuLight(event, this)" class="${classes}">${icon}</a>`;
  }
  const clickAttr = onClick ? `onclick="${onClick}"` : '';
  return `<button type="button" ${idAttr} ${clickAttr} ${titleAttr} ${ariaAttr} onmousemove="trackMenuLight(event, this)" class="${classes}">${icon}</button>`;
}

/**
 * Surface IconButton (.ds-icon-btn.ds-btn-surface) — Transparent by default; reveals Tonal background + animation on hover
 */
export function SurfaceIconButton(props = {}) {
  return IconButton({ ...props, variant: 'surface' });
}

/**
 * Master Component 3: Standardized Floating Pill (.ds-pill)
 * Shared frosted capsule container instanced for Top Scrolled Header Pill
 * and Mobile Bottom Showcase Pill.
 */
export function Pill({
  left = '',
  center = '',
  right = '',
  tag = 'div',
  controlsInset = false,
  ariaLabel = '',
  className = '',
  id = ''
}) {
  const classes = [
    'ds-pill',
    controlsInset ? 'ds-pill-controls' : '',
    className
  ].filter(Boolean).join(' ');
  const idAttr = id ? `id="${id}"` : '';
  const ariaAttr = ariaLabel ? `aria-label="${ariaLabel}"` : '';
  return `<${tag} ${idAttr} ${ariaAttr} class="${classes}">
    <div class="justify-self-start flex items-center">${left}</div>
    <div class="justify-self-center flex items-center">${center}</div>
    <div class="justify-self-end flex items-center">${right}</div>
  </${tag}>`;
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
