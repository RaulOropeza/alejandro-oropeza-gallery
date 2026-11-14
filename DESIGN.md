# Alejandro Oropeza Photo Gallery — Design System (`DESIGN.md`)

This document is the architectural contract for every UI component, token, style, and layout change in `alejandro-oropeza-gallery`.

## 1. Single Source of Truth

- **Tokens & CSS Components:** `src/styles/design-system.css`
- **Master HTML Builders & Live Specimen:** `scripts/manage_gallery.py`
  - `render_button(...)` — Tonal Button (`.ds-btn`)
  - `render_surface_button(...)` — Surface Button (`.ds-btn.ds-btn-surface`)
  - `render_icon_button(...)` — Tonal IconButton (`.ds-icon-btn`)
  - `render_surface_icon_button(...)` — Surface IconButton (`.ds-icon-btn.ds-btn-surface`)
  - `render_pill(...)` — Standardized Floating Pill (`.ds-pill`)
- **Live Specimen Output:** `dist/design-system.html` (mirrored to `docs/design-system.html`)

## 2. Core Tokens (`:root` in `src/styles/design-system.css`)

### Color & Glass (Strictly Neutral Achromatic `R = G = B`)
| Token | Value | Usage |
|---|---|---|
| `--ds-color-canvas` | `#FFFFFF` | Primary page & card surface |
| `--ds-color-subtle` | `#FAFAFA` | Subtle specimen / section backing |
| `--ds-color-stage` | `#F2F2F2` | Showcase stage backdrop |
| `--ds-color-placeholder` | `#EDEDED` | Image loading placeholder |
| `--ds-color-border` | `#EBEBEB` | Hairline rules & spec borders |
| `--ds-color-border-strong` | `#DCDCDC` | Stronger borders |
| `--ds-color-ink-primary` | `#141414` | Primary headings & active ink |
| `--ds-color-ink-secondary` | `#525252` | Body copy |
| `--ds-color-ink-muted` | `#737373` | Secondary metadata, counter, footer © |
| `--ds-color-ink-label` | `#8C8C8C` | Uppercase spec labels |
| `--ds-color-ink-inverse` | `#FFFFFF` | Hero & dark-surface ink |
| `--ds-pill-bg` / `--ds-pill-blur` / `--ds-pill-border` | `rgba(255,255,255,0.68)` / `blur(14px) saturate(140%)` / `rgba(255,255,255,0.78)` | Floating pill frosted glass |
| `--ds-surface-frosted` / `--ds-blur-frosted` | `rgba(255,255,255,0.76)` / `blur(16px) saturate(140%)` | Frosted surface panels |

### Responsive Controls, Spacing & Layout (8px Grid)
- **Buttons & IconButtons:** `--ds-control-size`: `56px` mobile (`< 768px`), `36px` desktop (`>= 768px`).
- **Icons inside controls:** `--ds-icon-size`: `20px` mobile, `18px` desktop (never hardcode `w-5 h-5` on control SVGs).
- **Button padding & gap:** `--ds-btn-padding-x: 16px`, `--ds-btn-gap: 0.5rem`.
- **Widths:** `--ds-pill-max-width: 46rem`, `--ds-details-max-width: 28rem` (mobile) / `40rem` (desktop), `--ds-gallery-max-width: 72rem`.
- **Radii:** `--ds-radius-sm: 0.25rem` (`4px` photo frames), `--ds-radius-pill: 9999px` (pills & buttons).

### Shadows & Motion
- **Shadows:** `--ds-pill-shadow`, `--ds-shadow-btn`, `--ds-shadow-btn-hover`, `--ds-shadow-btn-hero-hover`, `--ds-shadow-btn-active`, `--ds-shadow-btn-hero-active`, `--ds-shadow-sheet`, `--ds-hero-text-shadow`.
- **Motion:** `--ds-ease-out-expo` (`cubic-bezier(0.16, 1, 0.3, 1)`), `--ds-duration-fast` (`180ms`), `--ds-duration-header` (`350ms`), `--ds-duration-zoom` (`450ms`), `--ds-hover-scale` (`1.03`), `ds-scroll-bob` (`2.2s infinite`).

### Typography (Self-Hosted `Jost` + `Nunito Sans`)
- `.ds-h1`: Jost 400, uppercase, `28px` M / `30px` D.
- `.ds-h2`: Jost 500 M / 400 D, uppercase, `24px` M / `26px` D / `22px` scrolled pill.
- `.ds-h3`: Jost 500, uppercase, `20px`.
- `.ds-brand-name`: Jost 500, uppercase, `18px` base / `22px` D top-scroll / `16px` D pill.
- `.ds-brand-subtitle`: Nunito Sans, uppercase, `16px` M (300) / `13px` D (400).
- `.ds-body` (`18px`, 300), `.ds-value` (`16px`, 400), `.ds-label` (`14px`, 400 uppercase), `.ds-footer-copy` (`12px`, 400).
- Hero overlay: `.ds-scroll-cue-label` (`18px` M / `16px` D), `.ds-hero-tech` (`14px`, fades out on scroll).

## 3. Rules for Every Change

1. **Never hardcode raw hex colors, shadows, radii, or control sizes** in component HTML/JS — reference `--ds-*` tokens in `src/styles/design-system.css`.
2. **Reuse master builders** (`render_button`, `render_surface_button`, `render_icon_button`, `render_surface_icon_button`, `render_pill`) for all interactive controls.
3. **Update the Design System Specimen** (`#design-system-specimen` in `scripts/manage_gallery.py`) whenever a new token, typography role, or component variant is added.
4. **Always rebuild & verify** with `python3 scripts/manage_gallery.py build` and inspect both mobile (`390×844`) and desktop (`1280×800`).
