#!/usr/bin/env python3
"""
============================================================================
ALEJANDRO OROPEZA — GALLERY CONTENT MANAGER & DESIGN SYSTEM BUILDER
Usage:
  1. Build / sync website after editing tokens, components, or photos.json:
     python3 scripts/manage_gallery.py build

  2. Add a new photograph (auto-extracts EXIF Focal Length, f/, Shutter, ISO):
     python3 scripts/manage_gallery.py add /path/to/photo.jpg \
       --title "New Photo Title" \
       --location "City, Country · 2026" \
       --description "Description of the photograph." \
       --price "$240"
============================================================================
"""
import argparse
import base64
import io
import json
import re
import shutil
import sys
from pathlib import Path
from PIL import Image, ExifTags

ROOT_DIR = Path("/home/antigravity/alejandro-oropeza-gallery")
CSS_PATH = ROOT_DIR / "src" / "styles" / "design-system.css"
DATA_PATH = ROOT_DIR / "src" / "data" / "photos.json"
PUBLIC_PHOTOS_DIR = ROOT_DIR / "public" / "photos"
PUBLIC_FONTS_DIR = ROOT_DIR / "public" / "fonts"
INDEX_HTML_PATH = ROOT_DIR / "index.html"
ARTIFACT_HTML_PATH = Path(
    "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/face751d-8bf6-461a-95f9-87e2341e2540/alejandro_oropeza_site_and_design_system.html"
)


def extract_exif_metadata(img_path: Path) -> dict:
    defaults = {
        "focalLength": "50 mm",
        "aperture": "f/8.0",
        "shutterSpeed": "1/500s",
        "iso": "ISO 100",
    }
    try:
        im = Image.open(img_path)
        exif = im.getexif()
        if not exif:
            return defaults
        ifd = exif.get_ifd(0x8769)
        for k, v in ifd.items():
            tag = ExifTags.TAGS.get(k, k)
            if tag == "FocalLength" and v:
                defaults["focalLength"] = f"{int(round(float(v)))} mm"
            elif tag == "FNumber" and v:
                defaults["aperture"] = f"f/{float(v):.1f}"
            elif tag == "ExposureTime" and v:
                val = float(v)
                if val < 1.0 and val > 0:
                    defaults["shutterSpeed"] = f"1/{int(round(1.0 / val))}s"
                else:
                    defaults["shutterSpeed"] = f"{val}s"
            elif tag == "ISOSpeedRatings" and v:
                defaults["iso"] = f"ISO {v}"
    except Exception:
        pass
    return defaults


def ensure_public_photos(catalog: dict):
    PUBLIC_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    b64_map = {}
    b64_thumb_map = {}
    for p in catalog["photos"]:
        fname = p["file"]
        src_candidates = [
            PUBLIC_PHOTOS_DIR / "hi-res" / fname,
            PUBLIC_PHOTOS_DIR / fname,
            Path("/home/antigravity") / fname,
        ]
        found = next((c for c in src_candidates if c.exists()), None)
        if not found:
            raise FileNotFoundError(f"Could not find photograph file: {fname}")

        dest = PUBLIC_PHOTOS_DIR / fname
        if found != dest:
            shutil.copy2(found, dest)

        im = Image.open(dest)
        icc = im.info.get("icc_profile")
        save_kwargs = {"format": "JPEG", "optimize": True}
        if icc:
            save_kwargs["icc_profile"] = icc

        # Inline preview copy (3200px max edge for crisp Retina rendering inside single-file artifact)
        preview_im = im.copy()
        if max(preview_im.size) > 3200:
            preview_im.thumbnail((3200, 3200), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        preview_im.save(buf, quality=92, **save_kwargs)
        b64_map[p["id"]] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

        # Crisp Lanczos gallery thumbnail copy (1200px max edge)
        thumb_im = im.copy()
        if max(thumb_im.size) > 1200:
            thumb_im.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        tbuf = io.BytesIO()
        thumb_im.save(tbuf, quality=88, **save_kwargs)
        b64_thumb_map[p["id"]] = "data:image/jpeg;base64," + base64.b64encode(tbuf.getvalue()).decode("ascii")

    return b64_map, b64_thumb_map


def cmd_add(args):
    src_file = Path(args.photo_path).resolve()
    if not src_file.exists():
        print(f"Error: File not found: {src_file}", file=sys.stderr)
        sys.exit(1)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    PUBLIC_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    dest_file = PUBLIC_PHOTOS_DIR / src_file.name
    shutil.copy2(src_file, dest_file)

    im = Image.open(dest_file)
    w, h = im.size
    orientation = "landscape" if w >= h else "portrait"
    aspect_ratio = round(w / h, 3)
    exif_data = extract_exif_metadata(dest_file)

    slug = re.sub(r"[^a-z0-9]+", "-", args.title.lower()).strip("-")
    new_entry = {
        "id": slug,
        "title": args.title,
        "file": src_file.name,
        "orientation": orientation,
        "aspectRatio": aspect_ratio,
        "row": args.row or 3,
        "location": args.location,
        "exif": {
            "focalLength": args.focal or exif_data["focalLength"],
            "aperture": args.aperture or exif_data["aperture"],
            "shutterSpeed": args.shutter or exif_data["shutterSpeed"],
            "iso": args.iso or exif_data["iso"],
        },
        "description": args.description,
        "print": {
            "enabled": False,
            "price": args.price or "$240",
            "dimensions": "16 × 24 in" if orientation == "portrait" else "20 × 30 in",
            "providerUrl": f"https://example.com/prints/{slug}",
        },
    }

    catalog["photos"].append(new_entry)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Added '{args.title}' ({orientation}, {w}x{h}) to {DATA_PATH}")
    cmd_build(None)


DEV_SWITCHER_BAR = """  <!-- =========================================================================
       MODE SWITCHER BAR: LIVE WEBSITE vs DESIGN SYSTEM (/design-system)
       ========================================================================= -->
  <div class="bg-[var(--card)] border border-[var(--border)] rounded-t-xl px-3.5 py-2 flex flex-wrap items-center justify-between gap-2 z-50 relative">
    <div class="flex items-center gap-1.5">
      <button onclick="switchMode('website')" id="mode-btn-website" class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors bg-[var(--primary)] text-[var(--primary-foreground)]">
        Live Website
      </button>
      <button onclick="switchMode('design-system')" id="mode-btn-ds" class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:opacity-90">
        Design System &amp; Components (/design-system)
      </button>
    </div>
    <div class="flex items-center gap-3">
      <label class="flex items-center gap-1.5 text-xs text-[var(--muted-foreground)] cursor-pointer">
        <input type="checkbox" id="toggle-print-shop" onchange="togglePrintShop(this.checked)" class="rounded" />
        <span>Preview Print Shop Hooks</span>
      </label>
    </div>
  </div>"""

PROD_EXTRA_HEAD = """  <link rel="preload" href="fonts/jost-latin.woff2" as="font" type="font/woff2" crossorigin />
  <link rel="preload" href="fonts/nunito-sans-latin.woff2" as="font" type="font/woff2" crossorigin />
  <link rel="preload" as="image" href="__HERO_MOBILE_SRCSET__" media="(max-width: 767px)" fetchpriority="high" />
  <link rel="preload" as="image" href="__HERO_DESKTOP_SRC__" media="(min-width: 768px)" fetchpriority="high" />
  <link rel="icon" type="image/svg+xml" href="favicon.svg" />
  <link rel="canonical" href="https://alejandrooropeza.com/" />
  <!-- Open Graph / Social Sharing Metadata -->
  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://alejandrooropeza.com/" />
  <meta property="og:title" content="Alejandro Oropeza — Photo gallery" />
  <meta property="og:description" content="Travel photography studying architecture, wildlife, coastlines, and solitary figures in quiet isolation." />
  <meta property="og:image" content="photos/FishermanOnShoreline_Acapulco_2022_AOropeza.jpg" />
  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="Alejandro Oropeza — Photo gallery" />
  <meta name="twitter:description" content="Travel photography studying architecture, wildlife, coastlines, and solitary figures in quiet isolation." />
  <meta name="twitter:image" content="photos/FishermanOnShoreline_Acapulco_2022_AOropeza.jpg" />"""


# ============================================================================
# MASTER BUTTON COMPONENT HELPERS (Single Source of Truth)
# 1. render_button(..., variant='tonal'|'surface')      -> Pill Button (.ds-btn / .ds-btn-surface)
# 2. render_icon_button(..., variant='tonal'|'surface') -> Circular IconButton (.ds-icon-btn / .ds-btn-surface)
# ============================================================================

ICON_MARKUP = {
    "arrow-left": '<svg width="20" height="20" class="shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>',
    "arrow-right": '<svg width="20" height="20" class="shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
    "menu": '<svg width="20" height="20" class="shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/></svg>',
    "close": '<svg width="20" height="20" class="shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    "fullscreen": '<svg width="20" height="20" class="shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>',
    "instagram": '<span class="ds-icon-glyph ds-icon-glyph-ig"></span>',
    "500px": '<span class="ds-icon-glyph ds-icon-glyph-500px"></span>',
}


def render_button(
    label: str,
    *,
    variant: str = "tonal",
    icon_left: str | None = None,
    icon_right: str | None = None,
    onclick: str | None = None,
    href: str | None = None,
    elem_id: str | None = None,
    aria_label: str | None = None,
    extra_cls: str = "",
) -> str:
    """Master Component 1: Pill Button — 'tonal' (default) or 'surface' (.ds-btn-surface)."""
    variant_cls = "ds-btn-surface" if variant == "surface" else ""
    classes = " ".join(c for c in ["ds-btn", variant_cls, extra_cls, "focus:outline-none"] if c)
    attrs = [f'class="{classes}"', 'onmousemove="trackMenuLight(event, this)"']
    if elem_id:
        attrs.insert(0, f'id="{elem_id}"')
    if aria_label:
        attrs.append(f'aria-label="{aria_label}"')

    parts = []
    if icon_left:
        parts.append(ICON_MARKUP[icon_left])
    parts.append(f"<span>{label}</span>")
    if icon_right:
        parts.append(ICON_MARKUP[icon_right])
    inner = "".join(parts)

    if href:
        attrs.extend([f'href="{href}"', 'target="_blank"', 'rel="noopener noreferrer"'])
        return f'<a {" ".join(attrs)}>{inner}</a>'
    attrs.insert(0, 'type="button"')
    if onclick:
        attrs.append(f'onclick="{onclick}"')
    return f'<button {" ".join(attrs)}>{inner}</button>'


def render_surface_button(label: str, **kwargs) -> str:
    """Surface Button convenience wrapper (no resting background; reveals Tonal background + animation on hover)."""
    return render_button(label, variant="surface", **kwargs)


def render_icon_button(
    icon: str,
    *,
    variant: str = "tonal",
    onclick: str | None = None,
    href: str | None = None,
    elem_id: str | None = None,
    title: str | None = None,
    aria_label: str | None = None,
    extra_attrs: str = "",
    extra_cls: str = "",
) -> str:
    """Master Component 2: Circular IconButton — 'tonal' (default) or 'surface' (.ds-btn-surface)."""
    variant_cls = "ds-btn-surface" if variant == "surface" else ""
    classes = " ".join(c for c in ["ds-icon-btn", variant_cls, extra_cls, "focus:outline-none"] if c)
    attrs = [f'class="{classes}"', 'onmousemove="trackMenuLight(event, this)"']
    if elem_id:
        attrs.insert(0, f'id="{elem_id}"')
    if title:
        attrs.append(f'title="{title}"')
    if aria_label:
        attrs.append(f'aria-label="{aria_label}"')
    if extra_attrs:
        attrs.append(extra_attrs)

    inner = ICON_MARKUP[icon]
    if href:
        attrs.extend([f'href="{href}"', 'target="_blank"', 'rel="noopener noreferrer"'])
        return f'<a {" ".join(attrs)}>{inner}</a>'
    attrs.insert(0, 'type="button"')
    if onclick:
        attrs.append(f'onclick="{onclick}"')
    return f'<button {" ".join(attrs)}>{inner}</button>'


def render_surface_icon_button(icon: str, **kwargs) -> str:
    """Surface IconButton convenience wrapper (no resting background; reveals Tonal background + animation on hover)."""
    return render_icon_button(icon, variant="surface", **kwargs)


def render_pill(
    left_html: str,
    center_html: str,
    right_html: str,
    *,
    tag: str = "div",
    elem_id: str | None = None,
    aria_label: str | None = None,
    controls_inset: bool = False,
    left_id: str | None = None,
    right_id: str | None = None,
    extra_cls: str = "",
    extra_style: str = "",
) -> str:
    """Master Component 3: Standardized Floating Pill (.ds-pill)."""
    classes = " ".join(
        c for c in ["ds-pill", "ds-pill-controls" if controls_inset else "", extra_cls] if c
    )
    attrs = [f'class="{classes}"']
    if elem_id:
        attrs.insert(0, f'id="{elem_id}"')
    if aria_label:
        attrs.append(f'aria-label="{aria_label}"')
    if extra_style:
        attrs.append(f'style="{extra_style}"')

    l_id = f'id="{left_id}" ' if left_id else ""
    r_id = f'id="{right_id}" ' if right_id else ""
    return (
        f'<{" ".join([tag, *attrs])}>'
        f'<div {l_id}class="flex items-center justify-start justify-self-start z-10">{left_html}</div>'
        f'<div class="justify-self-center z-10">{center_html}</div>'
        f'<div {r_id}class="justify-self-end self-center z-10">{right_html}</div>'
        f"</{tag}>"
    )


def build_button_instances(catalog: dict) -> dict[str, str]:
    ig_url = catalog["site"]["social"]["instagram"].replace("&", "&amp;")
    px_url = catalog["site"]["social"]["fiveHundredPx"].replace("&", "&amp;")

    btn_hdr_back = render_button(
        "Gallery",
        icon_left="arrow-left",
        onclick="showView('gallery')",
        elem_id="hdr-left-back",
        extra_cls="ds-showcase-back is-hidden",
        aria_label="Back to gallery",
    )
    btn_mob_back = render_button(
        "Gallery",
        icon_left="arrow-left",
        onclick="showView('gallery')",
        aria_label="Back to gallery",
    )
    ibtn_hdr_ig = render_icon_button(
        "instagram",
        href=ig_url,
        title="Instagram (@alejandroropeza.photo)",
        aria_label="Instagram",
    )
    ibtn_hdr_500px = render_icon_button(
        "500px",
        href=px_url,
        title="500px (Alejandro Oropeza)",
        aria_label="500px",
    )
    ibtn_hdr_menu = render_icon_button(
        "menu",
        onclick="toggleMobileMenu()",
        elem_id="hdr-hamburger-btn",
        aria_label="Toggle navigation menu",
        extra_attrs='aria-expanded="false"',
        extra_cls="md:hidden",
    )
    ibtn_hdr_prev = render_icon_button(
        "arrow-left",
        onclick="stepPhoto(-1)",
        title="Previous photograph",
        aria_label="Previous photograph",
    )
    ibtn_hdr_next = render_icon_button(
        "arrow-right",
        onclick="stepPhoto(1)",
        title="Next photograph",
        aria_label="Next photograph",
    )
    ibtn_mob_prev = render_icon_button(
        "arrow-left",
        onclick="stepPhoto(-1)",
        title="Previous photograph",
        aria_label="Previous photograph",
    )
    ibtn_mob_next = render_icon_button(
        "arrow-right",
        onclick="stepPhoto(1)",
        title="Next photograph",
        aria_label="Next photograph",
    )

    # Mobile Home Vertical Social Stack (Lives inside the vertical menu pill, collapses on scroll)
    ibtn_mob_hero_ig = render_icon_button(
        "instagram",
        href=ig_url,
        elem_id="mob-hero-ig-btn",
        title="Instagram (@alejandroropeza.photo)",
        aria_label="Instagram",
    )
    ibtn_mob_hero_500px = render_icon_button(
        "500px",
        href=px_url,
        elem_id="mob-hero-500px-btn",
        title="500px (Alejandro Oropeza)",
        aria_label="500px",
    )
    mobile_social_stack = (
        f'<div id="mobile-social-stack" class="ds-mobile-social-stack" aria-label="Social links">'
        f"{ibtn_mob_hero_ig}{ibtn_mob_hero_500px}"
        f"</div>"
    )

    # Top Header Pill Instance
    top_header_pill = render_pill(
        left_html=(
            '<button onclick="showView(\'gallery\')" id="hdr-brand-name" '
            'class="ds-brand-name text-left hover:opacity-75 transition-opacity focus:outline-none">'
            '<span>Alejandro Oropeza</span>'
            '<span class="ds-brand-subtitle">Photo Gallery</span>'
            "</button>" + btn_hdr_back
        ),
        center_html=(
            '<nav id="header-menu-nav" class="ds-menu-nav">'
            '<button onclick="showView(\'gallery\')" onmousemove="trackMenuLight(event, this)" id="nav-gallery" class="ds-menu-link is-active focus:outline-none"><span class="ds-menu-text">GALLERY</span></button>'
            '<span class="ds-menu-sep">/</span>'
            '<button onclick="showView(\'about\')" onmousemove="trackMenuLight(event, this)" id="nav-about" class="ds-menu-link focus:outline-none"><span class="ds-menu-text">ABOUT ME</span></button>'
            "</nav>"
            '<div id="hdr-photo-title-wrap" class="hidden flex-col items-center justify-center text-center pointer-events-none px-2 max-w-[calc(100vw-2rem)] md:max-w-none">'
            '<span id="hdr-photo-title" class="ds-h2"></span>'
            "</div>"
        ),
        right_html=(
            f'<div id="header-main-nav" class="flex items-center justify-end gap-2">'
            f'<div class="ds-desktop-social">{ibtn_hdr_ig}{ibtn_hdr_500px}</div>'
            f"{ibtn_hdr_menu}"
            f"{mobile_social_stack}"
            f"</div>"
            f'<div id="header-photo-status" class="ds-showcase-status is-hidden items-center justify-end gap-2">'
            f'<span id="hdr-photo-counter" class="whitespace-nowrap">1 of 10</span>'
            f'<div class="flex items-center gap-2">{ibtn_hdr_prev}{ibtn_hdr_next}</div>'
            f"</div>"
        ),
        elem_id="floating-header-pill",
        left_id="hdr-left-col",
        right_id="hdr-right-col",
        extra_cls="ds-floating-pill",
    )

    # Mobile Bottom Showcase Pill Instance
    mob_showcase_pill = render_pill(
        left_html=btn_mob_back,
        center_html='<span id="mob-photo-counter" class="ds-mobile-tonal-counter">1 of 10</span>',
        right_html=f'<div class="flex items-center gap-2">{ibtn_mob_prev}{ibtn_mob_next}</div>',
        tag="nav",
        elem_id="mobile-showcase-bar",
        aria_label="Photo navigation",
        controls_inset=True,
        extra_cls="ds-mobile-showcase-bar hidden md:hidden",
    )

    # Design System Specimen Pills
    ds_ibtn_ig = render_icon_button("instagram", title="Instagram")
    ds_ibtn_500px = render_icon_button("500px", title="500px")
    ds_ibtn_prev = render_icon_button("arrow-left", title="Previous")
    ds_ibtn_next = render_icon_button("arrow-right", title="Next")

    ds_pill_header = render_pill(
        left_html='<span class="ds-brand-name">Alejandro Oropeza</span>',
        center_html=(
            '<nav class="ds-menu-nav">'
            '<button onmousemove="trackMenuLight(event, this)" class="ds-menu-link is-active focus:outline-none"><span class="ds-menu-text">GALLERY</span></button>'
            '<span class="ds-menu-sep">/</span>'
            '<button onmousemove="trackMenuLight(event, this)" class="ds-menu-link focus:outline-none"><span class="ds-menu-text">ABOUT ME</span></button>'
            "</nav>"
        ),
        right_html=f'<div class="flex items-center gap-2">{ds_ibtn_ig}{ds_ibtn_500px}</div>',
        extra_cls="mx-auto w-full",
    )

    ds_pill_mob_dock = render_pill(
        left_html=render_button("Gallery", icon_left="arrow-left"),
        center_html='<span class="ds-mobile-tonal-counter">2 of 10</span>',
        right_html=f'<div class="flex items-center gap-2">{ds_ibtn_prev}{ds_ibtn_next}</div>',
        controls_inset=True,
        extra_cls="mx-auto w-full max-w-[23rem]",
    )

    return {
        # Standardized Pill Instances & Mobile Hero Social Stack
        "__PILL_TOP_HEADER__": top_header_pill,
        "__MOBILE_SOCIAL_STACK__": mobile_social_stack,
        "__PILL_MOB_SHOWCASE__": mob_showcase_pill,
        # Live Website Instances — Button
        "__BTN_PRINT_ORDER__": render_button(
            "Order print",
            onclick="triggerPrintOrder(this)",
            elem_id="detail-print-btn",
        ),
        # Live Website Instances — IconButton
        "__IBTN_DRAWER_CLOSE__": render_icon_button(
            "close",
            onclick="toggleMobileMenu(false)",
            aria_label="Close menu",
        ),
        "__IBTN_DRAWER_IG__": render_icon_button(
            "instagram",
            href=ig_url,
            title="Instagram",
            aria_label="Instagram",
        ),
        "__IBTN_DRAWER_500PX__": render_icon_button(
            "500px",
            href=px_url,
            title="500px",
            aria_label="500px",
        ),
        "__IBTN_FOOT_IG__": render_icon_button(
            "instagram",
            href=ig_url,
            title="Instagram (@alejandroropeza.photo)",
            aria_label="Instagram",
        ),
        "__IBTN_FOOT_500PX__": render_icon_button(
            "500px",
            href=px_url,
            title="500px (Alejandro Oropeza)",
            aria_label="500px",
        ),
        # Live Website Instances — Stage Visualizer Trigger (Surface Button) & Popup Visualizer Close (Standard Tonal)
        "__SIBTN_STAGE_VISUALIZER__": render_surface_button(
            "Fullscreen",
            icon_left="fullscreen",
            onclick="openVisualizer()",
            elem_id="stage-visualizer-btn",
            aria_label="Open zoomable fullscreen view",
            extra_cls="ds-stage-visualizer-btn",
        ),
        "__SIBTN_VISUALIZER_CLOSE__": render_icon_button(
            "close",
            onclick="closeVisualizer()",
            elem_id="visualizer-close-btn",
            title="Close visualizer",
            aria_label="Close visualizer",
            extra_cls="ds-visualizer-close-btn",
        ),
        # Design System Specimen Instances — Tonal
        "__DS_BTN_LABEL_ONLY__": render_button("Order print"),
        "__DS_BTN_ICON_LEFT__": render_button("Back to gallery", icon_left="arrow-left"),
        "__DS_BTN_ICON_RIGHT__": render_button("Next photo", icon_right="arrow-right"),
        "__DS_IBTN_PREV__": ds_ibtn_prev,
        "__DS_IBTN_NEXT__": ds_ibtn_next,
        "__DS_IBTN_IG__": ds_ibtn_ig,
        "__DS_IBTN_500PX__": ds_ibtn_500px,
        "__DS_IBTN_MENU__": render_icon_button("menu", title="Menu"),
        "__DS_IBTN_CLOSE__": render_icon_button("close", title="Close"),
        "__DS_IBTN_FULLSCREEN__": render_icon_button("fullscreen", title="Fullscreen"),
        # Design System Specimen Instances — Surface (No resting background; Tonal background + animation on hover)
        "__DS_SBTN_LABEL_ONLY__": render_surface_button("Order print"),
        "__DS_SBTN_ICON_LEFT__": render_surface_button("Back to gallery", icon_left="arrow-left"),
        "__DS_SBTN_ICON_RIGHT__": render_surface_button("Next photo", icon_right="arrow-right"),
        "__DS_SIBTN_PREV__": render_surface_icon_button("arrow-left", title="Previous"),
        "__DS_SIBTN_NEXT__": render_surface_icon_button("arrow-right", title="Next"),
        "__DS_SIBTN_IG__": render_surface_icon_button("instagram", title="Instagram"),
        "__DS_SIBTN_500PX__": render_surface_icon_button("500px", title="500px"),
        "__DS_SIBTN_MENU__": render_surface_icon_button("menu", title="Menu"),
        "__DS_SIBTN_CLOSE__": render_surface_icon_button("close", title="Close"),
        "__DS_SIBTN_FULLSCREEN__": render_surface_icon_button("fullscreen", title="Fullscreen"),
        "__DS_PILL_HEADER__": ds_pill_header,
        "__DS_PILL_MOB_DOCK__": ds_pill_mob_dock,
    }


def build_html(design_system_css: str, catalog: dict, is_inline_embed: bool = False, is_production: bool = False) -> str:
    hero_height_cls = "h-[450px]" if is_inline_embed else "ds-viewport-height"
    stage_height_cls = "h-[450px]" if is_inline_embed else "ds-viewport-height"
    shell_cls = (
        "relative w-full max-h-[450px] overflow-y-auto rounded-b-xl shadow-sm"
        if is_inline_embed
        else "relative ds-viewport-min-height w-full"
    )
    ds_shell_cls = (
        "hidden w-full max-h-[450px] overflow-y-auto rounded-b-xl p-6 space-y-6"
        if is_inline_embed
        else "hidden max-w-5xl mx-auto px-6 sm:px-10 py-12 space-y-8"
    )
    header_pos_cls = "sticky top-0 left-0 right-0 z-50 px-4 md:px-10" if is_inline_embed else "fixed top-0 left-0 right-0 z-50 px-4 md:px-10"
    main_pull_cls = "-mt-[5rem]" if is_inline_embed else ""

    effective_css = design_system_css
    if is_production:
        body_cls = "bg-[var(--ds-color-canvas)] text-[var(--foreground)] antialiased p-0 m-0"
        shell_style = "background-color: var(--ds-color-canvas); color: var(--ds-color-ink-primary); border: none;"
        mode_switcher_bar = ""
        extra_head = PROD_EXTRA_HEAD
    else:
        body_cls = "bg-transparent text-[var(--foreground)] antialiased p-0 sm:p-2 select-none"
        shell_style = "background-color: var(--ds-color-canvas); color: var(--ds-color-ink-primary); border: 1px solid var(--ds-color-border); border-top: none;"
        mode_switcher_bar = DEV_SWITCHER_BAR
        extra_head = ""
        if PUBLIC_FONTS_DIR.exists():
            for woff_path in PUBLIC_FONTS_DIR.glob("*.woff2"):
                b64_font = base64.b64encode(woff_path.read_bytes()).decode("ascii")
                effective_css = effective_css.replace(
                    f"fonts/{woff_path.name}",
                    f"data:font/woff2;base64,{b64_font}",
                )

    tw_path = ROOT_DIR / "src" / "styles" / "tailwind-compiled.css"
    if tw_path.exists():
        tailwind_head = f"  <style>\n{tw_path.read_text(encoding='utf-8')}\n  </style>"
    else:
        tailwind_head = '  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>'

    hero_landscape = next(
        (p for p in catalog["photos"] if p["id"] == catalog["site"].get("heroPhotoId")),
        catalog["photos"][0],
    )
    hero_portrait = next(
        (p for p in catalog["photos"] if p.get("orientation") == "portrait"),
        hero_landscape,
    )
    hero_mobile_src = hero_portrait.get("heroSrc") or hero_portrait.get("src", "")
    hero_desktop_src = hero_landscape.get("heroSrc") or hero_landscape.get("src", "")

    html = HTML_BASE_TEMPLATE
    for token, rendered in build_button_instances(catalog).items():
        html = html.replace(token, rendered)
    html = html.replace("<!-- __EXTRA_HEAD__ -->", extra_head)
    html = html.replace("<!-- __TAILWIND_HEAD__ -->", tailwind_head)
    html = html.replace("/* __DESIGN_SYSTEM_CSS__ */", effective_css)
    html = html.replace("__CATALOG_JSON__", json.dumps(catalog, ensure_ascii=False))
    html = html.replace("__HERO_MOBILE_SRCSET__", hero_mobile_src)
    html = html.replace("__HERO_DESKTOP_SRC__", hero_desktop_src)
    html = html.replace("__HERO_HEIGHT_CLS__", hero_height_cls)
    html = html.replace("__STAGE_HEIGHT_CLS__", stage_height_cls)
    html = html.replace("__SHELL_CLS__", shell_cls)
    html = html.replace("__DS_SHELL_CLS__", ds_shell_cls)
    html = html.replace("__HEADER_POS_CLS__", header_pos_cls)
    html = html.replace("__MAIN_PULL_CLS__", main_pull_cls)
    html = html.replace("__BODY_CLS__", body_cls)
    html = html.replace("__SHELL_STYLE__", shell_style)
    html = html.replace("<!-- __MODE_SWITCHER_BAR__ -->", mode_switcher_bar)
    return html


def build_production(design_system_css: str, catalog: dict):
    dist_dir = ROOT_DIR / "dist"
    dist_photos_dir = dist_dir / "photos"
    dist_thumbs_dir = dist_photos_dir / "thumbs"
    dist_showcase_dir = dist_photos_dir / "showcase"
    dist_hero_dir = dist_photos_dir / "hero"
    dist_fonts_dir = dist_dir / "fonts"
    dist_thumbs_dir.mkdir(parents=True, exist_ok=True)
    dist_showcase_dir.mkdir(parents=True, exist_ok=True)
    dist_hero_dir.mkdir(parents=True, exist_ok=True)
    dist_fonts_dir.mkdir(parents=True, exist_ok=True)

    # 0. Copy self-hosted cross-device WOFF2 web fonts to dist/fonts/
    if PUBLIC_FONTS_DIR.exists():
        for woff_path in PUBLIC_FONTS_DIR.glob("*.woff2"):
            shutil.copy2(woff_path, dist_fonts_dir / woff_path.name)

    hero_landscape = next(
        (p for p in catalog["photos"] if p["id"] == catalog["site"].get("heroPhotoId")),
        catalog["photos"][0],
    )
    hero_portrait = next(
        (p for p in catalog["photos"] if p.get("orientation") == "portrait"),
        hero_landscape,
    )
    hero_ids = {hero_landscape["id"], hero_portrait["id"]}

    def save_tier(im_src: Image.Image, dest: Path, max_dim: int, quality: int, icc):
        tier_im = im_src.copy()
        if max(tier_im.size) > max_dim:
            tier_im.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        kw = {"format": "JPEG", "quality": quality, "optimize": True, "progressive": True}
        if icc:
            kw["icc_profile"] = icc
        tier_im.save(dest, **kw)

    # 1. Generate 3 web tiers from hi-res originals (3000px fullscreen, 1600px showcase, 1100px grid) + hero
    for p in catalog["photos"]:
        fname = p["file"]
        src = PUBLIC_PHOTOS_DIR / "hi-res" / fname
        if not src.exists():
            src = PUBLIC_PHOTOS_DIR / fname

        im = Image.open(src)
        icc = im.info.get("icc_profile")

        save_tier(im, dist_photos_dir / fname, 3000, 87, icc)
        save_tier(im, dist_showcase_dir / fname, 1600, 85, icc)
        save_tier(im, dist_thumbs_dir / fname, 1100, 83, icc)

        if p["id"] in hero_ids:
            max_hero = 1200 if p["id"] == hero_portrait["id"] and p.get("orientation") == "portrait" else 1920
            save_tier(im, dist_hero_dir / fname, max_hero, 84, icc)

    # 2. Build production catalog with relative fullscreen, showcase, thumbnail, and hero paths
    prod_catalog = json.loads(json.dumps(catalog))
    for p in prod_catalog["photos"]:
        p["src"] = f"photos/{p['file']}"
        p["showcaseSrc"] = f"photos/showcase/{p['file']}"
        p["thumbSrc"] = f"photos/thumbs/{p['file']}"
        if p["id"] in hero_ids:
            p["heroSrc"] = f"photos/hero/{p['file']}"

    # 3. Build dist/index.html (clean live site without dev bar, zero render-blocking scripts)
    prod_html = build_html(design_system_css, prod_catalog, is_inline_embed=False, is_production=True)
    with open(dist_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(prod_html)

    # 4. Build dist/favicon.svg (monochrome minimalist camera aperture)
    favicon_svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none">
  <circle cx="16" cy="16" r="14" stroke="#141414" stroke-width="2"/>
  <circle cx="16" cy="16" r="5" stroke="#141414" stroke-width="1.5"/>
  <path d="M16 2 L22 11 M28 10 L23 20 M26 24 L16 26 M11 29 L7 20 M3 20 L8 11 M5 8 L15 6" stroke="#141414" stroke-width="1.2" stroke-linecap="round"/>
</svg>"""
    with open(dist_dir / "favicon.svg", "w", encoding="utf-8") as f:
        f.write(favicon_svg)

    # 5. Build dist/design-system.html (standalone design system page)
    ds_page_html = prod_html.replace('id="scroll-viewport" class="relative ds-viewport-min-height w-full"', 'id="scroll-viewport" class="hidden relative ds-viewport-min-height w-full"')
    ds_page_html = ds_page_html.replace('id="design-system-viewport" class="hidden ', 'id="design-system-viewport" class="')
    with open(dist_dir / "design-system.html", "w", encoding="utf-8") as f:
        f.write(ds_page_html)

    # 5. Build dist/robots.txt and dist/sitemap.xml
    with open(dist_dir / "robots.txt", "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\nSitemap: https://alejandrooropeza.com/sitemap.xml\n")

    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://alejandrooropeza.com/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>
  <url><loc>https://alejandrooropeza.com/#/about</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>
"""
    for p in catalog["photos"]:
        sitemap_xml += f"  <url><loc>https://alejandrooropeza.com/#/photo/{p['id']}</loc><changefreq>monthly</changefreq><priority>0.9</priority></url>\n"
    sitemap_xml += "</urlset>\n"
    with open(dist_dir / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap_xml)

    # 6. Build dist/README.md deployment manual
    readme_md = """# Alejandro Oropeza — Production Distribution

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
"""
    with open(dist_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_md)

    # 7. Mirror dist/ to docs/ for automatic GitHub Pages deployment
    docs_dir = ROOT_DIR / "docs"
    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    shutil.copytree(dist_dir, docs_dir)
    with open(docs_dir / ".nojekyll", "w", encoding="utf-8") as f:
        pass

    print(f"Production build ready in {dist_dir} and mirrored to {docs_dir}")


def cmd_build(_args):
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        design_system_css = f.read()

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    b64_map, b64_thumb_map = ensure_public_photos(catalog)
    for p in catalog["photos"]:
        p["src"] = b64_map[p["id"]]
        p["thumbSrc"] = b64_thumb_map[p["id"]]

    # 1. Root index.html (local dev / preview server)
    full_html = build_html(design_system_css, catalog, is_inline_embed=False, is_production=False)
    with open(INDEX_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(full_html)

    # 2. Chat inline preview artifact
    if ARTIFACT_HTML_PATH.parent.exists():
        embed_html = build_html(design_system_css, catalog, is_inline_embed=True, is_production=False)
        with open(ARTIFACT_HTML_PATH, "w", encoding="utf-8") as f:
            f.write(embed_html)

    # 3. Clean production distribution in dist/
    build_production(design_system_css, catalog)

    print(f"Built {INDEX_HTML_PATH} ({len(full_html)} bytes) and synced live preview artifact.")
HTML_BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="default" />
  <title>Alejandro Oropeza — Photo gallery</title>
  <meta name="description" content="Alejandro Oropeza — Travel photography studying architecture, wildlife, coastlines, and solitary figures in quiet isolation." />
  <!-- __EXTRA_HEAD__ -->
  <!-- __TAILWIND_HEAD__ -->
  <style>
/* __DESIGN_SYSTEM_CSS__ */
  </style>
</head>
<body class="__BODY_CLS__" style="margin: 0;">

<!-- __MODE_SWITCHER_BAR__ -->

  <!-- =========================================================================
       MODE 1: THE LIVE WEBSITE SHELL
       ========================================================================= -->
  <div id="scroll-viewport" class="__SHELL_CLS__" style="__SHELL_STYLE__">

    <!-- FLOATING HEADER (Unscrolled: Full-Width Bar | Scrolled: Morphs into Standardized Floating Pill .ds-pill) -->
    <header id="floating-header" class="ds-floating-header ds-header-hero __HEADER_POS_CLS__">
      __PILL_TOP_HEADER__
    </header>

    <!-- MOBILE NAVIGATION OVERLAY & SHEET -->
    <div id="mobile-nav-overlay" class="ds-mobile-nav-overlay" onclick="if(event.target===this) toggleMobileMenu(false)">
      <div class="ds-mobile-nav-sheet">
        <div class="flex items-center justify-between pb-4 border-b border-[var(--ds-color-border)]">
          <span class="ds-brand-name">Alejandro Oropeza</span>
          __IBTN_DRAWER_CLOSE__
        </div>
        <nav class="flex flex-col py-6 space-y-2">
          <button onclick="mobileNavTo('gallery')" id="mob-nav-gallery" class="ds-mob-menu-link is-active focus:outline-none">
            <span>GALLERY</span>
            <span class="ds-mob-indicator"></span>
          </button>
          <button onclick="mobileNavTo('about')" id="mob-nav-about" class="ds-mob-menu-link focus:outline-none">
            <span>ABOUT ME</span>
            <span class="ds-mob-indicator"></span>
          </button>
        </nav>
        <div class="pt-4 border-t border-[var(--ds-color-border)] flex items-center justify-between">
          <span class="ds-label text-[10px]">CONNECT</span>
          <div class="flex items-center gap-2.5">
            __IBTN_DRAWER_IG__
            __IBTN_DRAWER_500PX__
          </div>
        </div>
      </div>
    </div>

    <!-- VIEW 1: GALLERY HOME PAGE -->
    <main id="view-gallery" class="__MAIN_PULL_CLS__">
      
      <!-- Full-Viewport-Height Main Image: Non-clickable, responsive picture (portrait photo on mobile, landscape on desktop) -->
      <section id="hero-banner" class="relative w-full __HERO_HEIGHT_CLS__ overflow-hidden" style="background-color: var(--ds-color-ink-primary);">
        <picture id="hero-picture" class="w-full h-full block">
          <source id="hero-source-mobile" media="(max-width: 767px)" srcset="__HERO_MOBILE_SRCSET__" />
          <img id="hero-featured-img" src="__HERO_DESKTOP_SRC__" fetchpriority="high" decoding="async" alt="Featured Photograph" class="w-full h-full object-cover object-center pointer-events-none" />
        </picture>
        <div class="ds-hero-mobile-brand md:hidden" aria-hidden="true">
          <span>Alejandro</span>
          <span>Oropeza</span>
          <span class="ds-brand-subtitle">Photo Gallery</span>
        </div>
        <div class="absolute inset-x-0 bottom-0 h-36 pointer-events-none" style="background: linear-gradient(to top, rgba(0,0,0,0.52) 0%, rgba(0,0,0,0) 100%);">
          <!-- Technical details (Mobile: centered above View gallery cue | Desktop: bottom-right) -->
          <span id="hero-tech-details" class="ds-hero-tech"></span>
          <!-- Scroll signifier (bottom-center): label + softly bobbing arrow -->
          <button type="button" id="hero-scroll-cue" onclick="scrollPastHero()" class="ds-scroll-cue absolute left-1/2 -translate-x-1/2 bottom-4 pointer-events-auto focus:outline-none" aria-label="View gallery">
            <span class="ds-scroll-cue-label">View gallery</span>
            <svg class="ds-scroll-cue-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          </button>
        </div>
      </section>

      <!-- Gallery Grid Section (All spacing values strict multiples of 8px) -->
      <div class="ds-gallery-section px-4 md:px-10 pt-16 pb-16 md:pt-20 md:pb-24">
        <div class="ds-gallery-intro max-w-2xl mx-auto text-center mb-16 md:mb-20">
          <h1 id="gallery-intro-h1" class="ds-h1">Explore the gallery</h1>
          <p id="gallery-intro-body" class="ds-body mt-4 md:mt-6"></p>
        </div>
        <div id="gallery-rows-container" class="ds-gallery-grid"></div>
      </div>

    </main>

    <!-- VIEW 2: PHOTO SHOWCASE PAGE -->
    <section id="view-detail" class="hidden __MAIN_PULL_CLS__">
      
      <!-- Dynamic-Viewport-Height Light Neutral Grey Photo Stage (.ds-showcase-stage) -->
      <div class="ds-showcase-stage relative w-full __STAGE_HEIGHT_CLS__ flex items-center justify-center overflow-hidden">
        <div class="w-full h-full flex items-center justify-center">
          <img id="detail-img" decoding="sync" alt="Selected Photograph" class="max-h-full max-w-full object-contain shadow-sm mx-auto block" />
        </div>
        <!-- Bottom-Right Fullscreen Visualizer Trigger (Surface IconButton) -->
        __SIBTN_STAGE_VISUALIZER__
      </div>

      <!-- Pure White Spec Sheet & Description Band Below Stage (.ds-showcase-details) -->
      <div class="ds-showcase-details">
        <div class="ds-showcase-details-inner">
          <div style="text-align: center;" class="text-center">
            <h2 class="ds-h3">Photo details</h2>
          </div>

          <div id="detail-spec-table" class="mt-6"></div>

          <!-- Optional Print Shop Hook (Uses Tonal Master Button .ds-btn) -->
          <div id="detail-print-hook" class="hidden mt-4 pt-4 flex items-center justify-between" style="border-top: 1px solid var(--ds-color-border);">
            <div>
              <span class="ds-label block">ARCHIVAL PRINT</span>
              <span id="detail-print-meta" class="ds-value">16 × 24 in · $240</span>
            </div>
            __BTN_PRINT_ORDER__
          </div>

          <!-- Centered DESCRIPTION (.ds-h3 + .ds-body) -->
          <div class="ds-showcase-desc mt-12 md:mt-16">
            <h3 class="ds-h3 text-center">DESCRIPTION</h3>
            <p id="dt-desc" class="ds-body mt-6 text-center"></p>
          </div>
        </div>
      </div>

      <!-- FLOATING BOTTOM SHOWCASE CONTROLS (Mobile Only — Standardized .ds-pill Instance) -->
      __PILL_MOB_SHOWCASE__

    </section>

    <!-- VIEW 3: ABOUT ME PAGE -->
    <section id="view-about" class="hidden __MAIN_PULL_CLS__ pt-24 px-6 sm:px-8 pb-16 max-w-xl mx-auto">
      <span id="about-kicker" class="ds-label block">ABOUT ME</span>
      <h1 id="about-heading" class="ds-brand-name mt-2">Alejandro Oropeza</h1>
      <p id="about-bio" class="ds-body mt-4"></p>
      <div id="about-specs" class="mt-6 pt-4" style="border-top: 1px solid var(--ds-color-border);"></div>
    </section>

    <!-- SITE FOOTER (Option 1 · Mirror of the Top Bar): Wordmark · Menu · Tonal IconButtons, thin rule above, muted © below -->
    <footer id="site-footer" class="ds-footer ds-header-transparent-dark">
      <div class="ds-footer-row">
        <button onclick="showView('gallery')" class="ds-brand-name ds-footer-brand text-left hover:opacity-75 transition-opacity focus:outline-none">Alejandro Oropeza</button>
        <nav class="ds-menu-nav ds-footer-menu">
          <button onclick="showView('gallery')" onmousemove="trackMenuLight(event, this)" id="foot-nav-gallery" class="ds-menu-link is-active focus:outline-none">
            <span class="ds-menu-text">GALLERY</span>
          </button>
          <span class="ds-menu-sep">/</span>
          <button onclick="showView('about')" onmousemove="trackMenuLight(event, this)" id="foot-nav-about" class="ds-menu-link focus:outline-none">
            <span class="ds-menu-text">ABOUT ME</span>
          </button>
        </nav>
        <div class="ds-footer-social">
          __IBTN_FOOT_IG__
          __IBTN_FOOT_500PX__
        </div>
      </div>
      <p class="ds-footer-copy">© 2026 Alejandro Oropeza</p>
    </footer>

  </div>

  <!-- ZOOMABLE POPUP PHOTO VISUALIZER (In-browser modal, edge-to-edge zero-radius framing, zoom & pan) -->
  <div id="photo-visualizer" class="ds-visualizer ds-header-hero" role="dialog" aria-modal="true" aria-hidden="true" aria-label="Zoomable photograph visualizer">
    <img id="visualizer-img" decoding="sync" draggable="false" alt="Photograph" />
    __SIBTN_VISUALIZER_CLOSE__
  </div>

  <!-- =========================================================================
       MODE 2: LIVING DESIGN SYSTEM & COMPONENT LIBRARY (/design-system)
       ========================================================================= -->
  <div id="design-system-viewport" class="__DS_SHELL_CLS__" style="background-color: #FFFFFF; color: #141414; border: 1px solid #E5E5E5; border-top: none;">
    
    <div class="pb-3" style="border-bottom: 1px solid var(--ds-color-border);">
      <span class="ds-label">SINGLE SOURCE OF TRUTH · src/styles/design-system.css</span>
      <h1 class="ds-h1 mt-1">Design System &amp; Component Library</h1>
      <p class="ds-body mt-1">
        Every page on the website imports these exact classes and CSS variables. Editing any rule in <code>src/styles/design-system.css</code> cascades automatically to all pages.
      </p>
    </div>

    <!-- 1. UNIFIED COMPONENT ARCHITECTURE (Tonal & Surface Buttons + Standardized Pill) -->
    <div>
      <h2 class="ds-h3 mb-2.5">1. Unified Component System (Tonal &amp; Surface Buttons · Standardized Pill · 56px M / 36px D)</h2>
      <div class="space-y-4 rounded-lg p-4" style="background-color: var(--ds-color-subtle); border: 1px solid var(--ds-color-border);">
        
        <!-- TONAL BUTTON (.ds-btn) -->
        <div class="pb-3.5" style="border-bottom: 1px solid var(--ds-color-border);">
          <div class="flex flex-wrap items-baseline justify-between gap-2 mb-2.5">
            <span class="ds-value font-medium">Tonal Button (<code>.ds-btn</code> · <code>render_button()</code>)</span>
            <span class="ds-label">Mobile: 56px high (20px icons) · Desktop: 36px high (18px icons) · 16px side padding</span>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            __DS_BTN_LABEL_ONLY__
            __DS_BTN_ICON_LEFT__
            __DS_BTN_ICON_RIGHT__
          </div>
        </div>

        <!-- SURFACE BUTTON (.ds-btn.ds-btn-surface) -->
        <div class="pb-3.5" style="border-bottom: 1px solid var(--ds-color-border);">
          <div class="flex flex-wrap items-baseline justify-between gap-2 mb-2.5">
            <span class="ds-value font-medium">Surface Button (<code>.ds-btn.ds-btn-surface</code> · <code>render_surface_button()</code> / <code>variant="surface"</code>)</span>
            <span class="ds-label">No background at rest · Tonal background, radial light sheen &amp; elevation appear on hover</span>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            __DS_SBTN_LABEL_ONLY__
            __DS_SBTN_ICON_LEFT__
            __DS_SBTN_ICON_RIGHT__
          </div>
        </div>

        <!-- TONAL ICON BUTTON (.ds-icon-btn) -->
        <div class="pb-3.5" style="border-bottom: 1px solid var(--ds-color-border);">
          <div class="flex flex-wrap items-baseline justify-between gap-2 mb-2.5">
            <span class="ds-value font-medium">Tonal IconButton (<code>.ds-icon-btn</code> · <code>render_icon_button()</code>)</span>
            <span class="ds-label">Mobile: 56px × 56px (20px icons) · Desktop: 36px × 36px (18px icons) · Shared hover &amp; press physics</span>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            __DS_IBTN_PREV__
            __DS_IBTN_NEXT__
            __DS_IBTN_FULLSCREEN__
            __DS_IBTN_IG__
            __DS_IBTN_500PX__
            __DS_IBTN_MENU__
            __DS_IBTN_CLOSE__
          </div>
        </div>

        <!-- SURFACE ICON BUTTON (.ds-icon-btn.ds-btn-surface) -->
        <div class="pb-3.5" style="border-bottom: 1px solid var(--ds-color-border);">
          <div class="flex flex-wrap items-baseline justify-between gap-2 mb-2.5">
            <span class="ds-value font-medium">Surface IconButton (<code>.ds-icon-btn.ds-btn-surface</code> · <code>render_surface_icon_button()</code> / <code>variant="surface"</code>)</span>
            <span class="ds-label">No background at rest · Tonal circular background &amp; radial light sheen appear on hover</span>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            __DS_SIBTN_PREV__
            __DS_SIBTN_NEXT__
            __DS_SIBTN_FULLSCREEN__
            __DS_SIBTN_IG__
            __DS_SIBTN_500PX__
            __DS_SIBTN_MENU__
            __DS_SIBTN_CLOSE__
          </div>
        </div>

        <!-- STANDARDIZED FLOATING PILL (.ds-pill) -->
        <div class="pb-3.5 space-y-2.5" style="border-bottom: 1px solid var(--ds-color-border);">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <span class="ds-value font-medium">Standardized Floating Pill (<code>.ds-pill</code> · <code>render_pill()</code>)</span>
            <span class="ds-label">Shared frosted capsule tokens (<code>--ds-pill-*</code>) instanced for Top Scrolled Header &amp; Mobile Bottom Dock</span>
          </div>
          <div class="p-3.5 rounded space-y-3" style="background: linear-gradient(90deg, #E2E2E2 0%, #F5F5F5 50%, #D9D9D9 100%);">
            __DS_PILL_HEADER__
            __DS_PILL_MOB_DOCK__
          </div>
        </div>

        <!-- DARK HERO CONTEXT ADAPTATION -->
        <div class="space-y-2.5">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <span class="ds-value font-medium">Automatic Context Adaptation (Hero Dark Glass vs. Light Surface)</span>
            <span class="ds-label">Both Tonal and Surface variants automatically adapt to dark Hero glass and light surfaces</span>
          </div>
          <!-- Hero State Specimen -->
          <div class="p-4 rounded grid grid-cols-[1fr_auto_1fr] items-center content-center ds-header-hero" style="background-color: #141414; color: #FFFFFF;">
            <div class="flex items-center gap-3 justify-self-start">
              <span class="ds-brand-name" style="color: #FFFFFF;">Alejandro Oropeza</span>
              __DS_SBTN_ICON_LEFT__
            </div>
            <nav class="ds-menu-nav justify-self-center">
              <button onmousemove="trackMenuLight(event, this)" class="ds-menu-link is-active focus:outline-none">
                <span class="ds-menu-text">GALLERY</span>
              </button>
              <span class="ds-menu-sep">/</span>
              <button onmousemove="trackMenuLight(event, this)" class="ds-menu-link focus:outline-none">
                <span class="ds-menu-text">ABOUT ME</span>
              </button>
            </nav>
            <div class="flex items-center gap-2 justify-self-end self-center">
              __DS_SIBTN_IG__
              __DS_IBTN_IG__
              __DS_IBTN_500PX__
            </div>
          </div>
        </div>

        <!-- HERO OVERLAY & SHOWCASE DETAILS SPECIMENS -->
        <div class="pt-3 space-y-2.5" style="border-top: 1px solid var(--ds-color-border);">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <span class="ds-value font-medium">Hero Overlay &amp; Showcase Patterns (<code>.ds-scroll-cue</code> · <code>.ds-hero-tech</code> · <code>.ds-spec-row</code>)</span>
            <span class="ds-label">Hero cue (18px M / 16px D) · Tech EXIF (14px, fades on scroll) · Spec rows (<code>--ds-details-max-width</code>: 28rem M / 40rem D)</span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div class="relative rounded h-32 flex items-center justify-center overflow-hidden" style="background: linear-gradient(180deg, #262626 0%, #141414 100%);">
              <span class="ds-hero-tech" style="position: static; transform: none; margin-bottom: 2.25rem;">Sony ILCE-7M4 · 35mm · f/4.0 · 1/500s · ISO 100</span>
              <div class="ds-scroll-cue" style="position: absolute; bottom: 0.75rem; left: 50%; transform: translateX(-50%); pointer-events: none;">
                <span class="ds-scroll-cue-label">View gallery</span>
                <svg class="ds-scroll-cue-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
              </div>
            </div>
            <div class="p-3.5 rounded border" style="background-color: var(--ds-color-canvas); border-color: var(--ds-color-border);">
              <div class="ds-spec-row"><span class="ds-label">LOCATION &amp; YEAR</span><span class="ds-value">Acapulco, 2024</span></div>
              <div class="ds-spec-row"><span class="ds-label">FOCAL LENGTH</span><span class="ds-value">135 mm</span></div>
              <div class="ds-spec-row" style="border-bottom: none;"><span class="ds-label">SHUTTER SPEED</span><span class="ds-value">1/1000 s</span></div>
            </div>
          </div>
        </div>

        <!-- SITE FOOTER SPECIMEN -->
        <div class="pt-3 space-y-2.5" style="border-top: 1px solid var(--ds-color-border);">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <span class="ds-value font-medium">Site Footer (<code>.ds-footer</code>)</span>
            <span class="ds-label">Mirror of the Top Bar · Wordmark · Menu · Tonal IconButtons · Thin rule above · Muted © (12px)</span>
          </div>
          <div class="rounded overflow-hidden" style="background-color: var(--ds-color-canvas);">
            <footer class="ds-footer ds-header-transparent-dark ds-footer-specimen">
              <div class="ds-footer-row">
                <button class="ds-brand-name ds-footer-brand text-left hover:opacity-75 transition-opacity focus:outline-none">Alejandro Oropeza</button>
                <nav class="ds-menu-nav ds-footer-menu">
                  <button onmousemove="trackMenuLight(event, this)" class="ds-menu-link is-active focus:outline-none">
                    <span class="ds-menu-text">GALLERY</span>
                  </button>
                  <span class="ds-menu-sep">/</span>
                  <button onmousemove="trackMenuLight(event, this)" class="ds-menu-link focus:outline-none">
                    <span class="ds-menu-text">ABOUT ME</span>
                  </button>
                </nav>
                <div class="ds-footer-social">
                  __DS_IBTN_IG__
                  __DS_IBTN_500PX__
                </div>
              </div>
              <p class="ds-footer-copy">© 2026 Alejandro Oropeza</p>
            </footer>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. TYPOGRAPHY HIERARCHY -->
    <div>
      <h2 class="ds-h3 mb-2.5">2. Typography Hierarchy (Self-Hosted Cross-Device WOFF2: Jost + Nunito Sans)</h2>
      <div class="space-y-2.5 rounded-lg p-3.5" style="background-color: var(--ds-color-subtle); border: 1px solid var(--ds-color-border);">
        <div class="ds-spec-row">
          <div>
            <span class="ds-label block">.ds-h1 · Jost Regular (400) · Uppercase · +0.04em</span>
            <span class="ds-h1 mt-0.5 block">Explore the gallery</span>
          </div>
          <code class="text-xs text-neutral-500">28px M · 30px D / 400</code>
        </div>
        <div class="ds-spec-row">
          <div>
            <span class="ds-label block">.ds-h2 · Jost Medium (500) / Regular (400 D) · Uppercase · +0.05em</span>
            <span class="ds-h2 mt-0.5 block">Perch Rock Lighthouse</span>
          </div>
          <code class="text-xs text-neutral-500">24px M · 26px D · 22px Pill</code>
        </div>
        <div class="ds-spec-row">
          <div>
            <span class="ds-label block">.ds-h3 · Jost Medium (500) · Uppercase · +0.12em</span>
            <span class="ds-h3 mt-0.5 block">PHOTO DETAILS / DESCRIPTION</span>
          </div>
          <code class="text-xs text-neutral-500">20px / 500</code>
        </div>
        <div class="ds-spec-row">
          <div>
            <span class="ds-label block">.ds-brand-name · Jost Medium (500) · Uppercase · +0.05em</span>
            <span class="ds-brand-name mt-0.5 block">Alejandro Oropeza</span>
          </div>
          <code class="text-xs text-neutral-500">18px Base · 22px D Top · 16px Pill</code>
        </div>
        <div class="ds-spec-row">
          <div>
            <span class="ds-label block">.ds-brand-subtitle · Nunito Sans · Uppercase · +0.16em</span>
            <span class="ds-brand-subtitle mt-0.5 block">Photo Gallery</span>
          </div>
          <code class="text-xs text-neutral-500">16px M (300) · 13px D (400)</code>
        </div>
        <div class="ds-spec-row">
          <div>
            <span class="ds-label block">.ds-body (18px) / .ds-value (16px) / .ds-label (14px) · Nunito Sans</span>
            <span class="ds-body mt-0.5 block">Travel photography studying subjects in quiet isolation.</span>
          </div>
          <code class="text-xs text-neutral-500">18px / 300–400</code>
        </div>
        <div class="ds-spec-row" style="border-bottom: none;">
          <div>
            <span class="ds-label block">.ds-footer-copy · Nunito Sans Regular (400) · +0.03em</span>
            <span class="ds-footer-copy mt-0.5 block" style="text-align: left; margin-top: 0.25rem;">© 2026 Alejandro Oropeza</span>
          </div>
          <code class="text-xs text-neutral-500">12px / 400</code>
        </div>
      </div>
    </div>

    <!-- 3. PURE MONOCHROME COLOR & GLASS TOKENS -->
    <div>
      <h2 class="ds-h3 mb-2.5">3. Pure Neutral Monochrome &amp; Glass Tokens (R = G = B)</h2>
      <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2.5">
        <div class="p-2.5 rounded border" style="background-color: var(--ds-color-canvas); border-color: var(--ds-color-border);">
          <div class="ds-value">#FFFFFF</div>
          <div class="ds-label mt-0.5">--ds-color-canvas</div>
        </div>
        <div class="p-2.5 rounded border" style="background-color: var(--ds-color-subtle); border-color: var(--ds-color-border);">
          <div class="ds-value">#FAFAFA</div>
          <div class="ds-label mt-0.5">--ds-color-subtle</div>
        </div>
        <div class="p-2.5 rounded border" style="background-color: var(--ds-color-stage); border-color: var(--ds-color-border-strong);">
          <div class="ds-value">#F2F2F2</div>
          <div class="ds-label mt-0.5">--ds-color-stage</div>
        </div>
        <div class="p-2.5 rounded border" style="background-color: var(--ds-color-placeholder); border-color: var(--ds-color-border-strong);">
          <div class="ds-value">#EDEDED</div>
          <div class="ds-label mt-0.5">--ds-color-placeholder</div>
        </div>
        <div class="p-2.5 rounded border" style="background-color: var(--ds-color-border); border-color: var(--ds-color-border-strong);">
          <div class="ds-value">#EBEBEB</div>
          <div class="ds-label mt-0.5">--ds-color-border</div>
        </div>
        <div class="p-2.5 rounded border" style="background-color: var(--ds-color-border-strong); border-color: var(--ds-color-border-strong);">
          <div class="ds-value">#DCDCDC</div>
          <div class="ds-label mt-0.5">--ds-color-border-strong</div>
        </div>
        <div class="p-2.5 rounded border" style="background-color: var(--ds-color-ink-label); border-color: var(--ds-color-ink-label);">
          <div class="ds-value" style="color: #FFFFFF;">#8C8C8C</div>
          <div class="ds-label mt-0.5" style="color: #F2F2F2;">--ds-color-ink-label</div>
        </div>
        <div class="p-2.5 rounded border" style="background-color: var(--ds-color-ink-muted); border-color: var(--ds-color-ink-muted);">
          <div class="ds-value" style="color: #FFFFFF;">#737373</div>
          <div class="ds-label mt-0.5" style="color: #EBEBEB;">--ds-color-ink-muted</div>
        </div>
        <div class="p-2.5 rounded border" style="background-color: var(--ds-color-ink-secondary); border-color: var(--ds-color-ink-secondary);">
          <div class="ds-value" style="color: #FFFFFF;">#525252</div>
          <div class="ds-label mt-0.5" style="color: #D4D4D4;">--ds-color-ink-secondary</div>
        </div>
        <div class="p-2.5 rounded border" style="background-color: var(--ds-color-ink-primary); border-color: var(--ds-color-ink-primary);">
          <div class="ds-value" style="color: #FFFFFF;">#141414</div>
          <div class="ds-label mt-0.5" style="color: #A3A3A3;">--ds-color-ink-primary</div>
        </div>
        <div class="p-2.5 rounded border" style="background: var(--ds-pill-bg); backdrop-filter: var(--ds-pill-blur); border-color: var(--ds-color-border-strong);">
          <div class="ds-value">68% Glass</div>
          <div class="ds-label mt-0.5">--ds-pill-bg</div>
        </div>
        <div class="p-2.5 rounded border" style="background: var(--ds-surface-frosted); backdrop-filter: var(--ds-blur-frosted); border-color: var(--ds-border-frosted);">
          <div class="ds-value">76% Glass</div>
          <div class="ds-label mt-0.5">--ds-surface-frosted</div>
        </div>
      </div>
    </div>

    <!-- 4. CORNER RADII, SHADOWS & ELEVATION -->
    <div>
      <h2 class="ds-h3 mb-2.5">4. Corner Radii, Shadows &amp; Elevation</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        <div class="p-3.5 rounded-lg border flex items-center gap-3" style="background-color: var(--ds-color-subtle); border-color: var(--ds-color-border);">
          <div class="w-10 h-10 shrink-0" style="background-color: var(--ds-color-stage); border: 1px solid var(--ds-color-border-strong); border-radius: var(--ds-radius-sm);"></div>
          <div><div class="ds-value">--ds-radius-sm</div><div class="ds-label">4px · Photo frames</div></div>
        </div>
        <div class="p-3.5 rounded-lg border flex items-center gap-3" style="background-color: var(--ds-color-subtle); border-color: var(--ds-color-border);">
          <div class="w-10 h-10 shrink-0" style="background-color: var(--ds-color-stage); border: 1px solid var(--ds-color-border-strong); border-radius: var(--ds-radius-pill);"></div>
          <div><div class="ds-value">--ds-radius-pill</div><div class="ds-label">9999px · Pills &amp; buttons</div></div>
        </div>
        <div class="p-3.5 rounded-lg border flex items-center gap-3" style="background-color: var(--ds-color-subtle); border-color: var(--ds-color-border);">
          <div class="w-10 h-10 shrink-0" style="background-color: var(--ds-pill-bg); border: 1px solid var(--ds-pill-border); border-radius: var(--ds-radius-pill); box-shadow: var(--ds-pill-shadow);"></div>
          <div><div class="ds-value">--ds-pill-shadow</div><div class="ds-label">Floating pill elevation</div></div>
        </div>
        <div class="p-3.5 rounded-lg border flex items-center gap-3" style="background-color: var(--ds-color-subtle); border-color: var(--ds-color-border);">
          <div class="w-10 h-10 shrink-0" style="background-color: var(--ds-color-canvas); border-radius: var(--ds-radius-pill); box-shadow: var(--ds-shadow-btn);"></div>
          <div><div class="ds-value">--ds-shadow-btn</div><div class="ds-label">Control resting border &amp; bevel</div></div>
        </div>
        <div class="p-3.5 rounded-lg border flex items-center gap-3" style="background-color: var(--ds-color-subtle); border-color: var(--ds-color-border);">
          <div class="w-10 h-10 shrink-0" style="background-color: var(--ds-color-canvas); border-radius: var(--ds-radius-pill); box-shadow: var(--ds-shadow-btn-hover);"></div>
          <div><div class="ds-value">--ds-shadow-btn-hover</div><div class="ds-label">Control hover lift</div></div>
        </div>
        <div class="p-3.5 rounded-lg border flex items-center gap-3" style="background-color: #1F1F1F; border-color: #1F1F1F;">
          <span class="ds-brand-name" style="color: #FFFFFF; text-shadow: var(--ds-hero-text-shadow); font-size: 0.875rem;">Aa</span>
          <div><div class="ds-value" style="color: #FFFFFF;">--ds-hero-text-shadow</div><div class="ds-label" style="color: #A3A3A3;">Hero title legibility</div></div>
        </div>
      </div>
    </div>

    <!-- 5. MOTION, ANIMATION & LAYOUT TOKENS -->
    <div>
      <h2 class="ds-h3 mb-2.5">5. Motion, Animation &amp; Layout Tokens</h2>
      <div class="space-y-2 rounded-lg p-3.5" style="background-color: var(--ds-color-subtle); border: 1px solid var(--ds-color-border);">
        <div class="ds-spec-row"><span class="ds-label">EASING &amp; DURATIONS</span><span class="ds-value"><code>--ds-ease-out-expo</code> · 180ms fast · 350ms header · 450ms zoom</span></div>
        <div class="ds-spec-row"><span class="ds-label">GALLERY HOVER &amp; CUE</span><span class="ds-value"><code>--ds-hover-scale</code> (1.03) · <code>ds-scroll-bob</code> (2.2s infinite)</span></div>
        <div class="ds-spec-row" style="border-bottom: none;"><span class="ds-label">LAYOUT WIDTHS (8PX GRID)</span><span class="ds-value"><code>--ds-pill-max-width</code> (46rem) · <code>--ds-details-max-width</code> (28rem M / 40rem D) · <code>--ds-gallery-max-width</code> (72rem)</span></div>
      </div>
    </div>

  </div>

  <script>
    const CATALOG = __CATALOG_JSON__;
    const PHOTOS = CATALOG.photos;

    let currentIdx = 0;
    let currentView = 'gallery';
    let isVisualizerOpen = false;
    let printShopPreview = CATALOG.site.printShopGlobalEnabled || false;

    const scrollViewport = document.getElementById('scroll-viewport');
    const floatingHeader = document.getElementById('floating-header');

    /* Cursor-Following Radial Light Illumination Handler for Menu Links & Tonal Buttons */
    function trackMenuLight(e, el) {
      const pillRect = el.getBoundingClientRect();
      el.style.setProperty('--pill-x', `${e.clientX - pillRect.left}px`);
      el.style.setProperty('--pill-y', `${e.clientY - pillRect.top}px`);
      const targetEl = el.querySelector('.ds-menu-text, .ds-icon-glyph') || el;
      const rect = targetEl.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      el.style.setProperty('--spot-x', `${x}px`);
      el.style.setProperty('--spot-y', `${y}px`);
    }

    /* Scroll signifier: glide past the full-height hero to the gallery */
    function scrollPastHero() {
      const hero = document.getElementById('hero-banner');
      const top = hero ? hero.offsetHeight : window.innerHeight;
      if (scrollViewport.scrollHeight > scrollViewport.clientHeight) {
        scrollViewport.scrollTo({ top, behavior: 'smooth' });
      } else {
        window.scrollTo({ top: hero.getBoundingClientRect().bottom + window.scrollY, behavior: 'smooth' });
      }
    }

    let lastHeaderStateKey = '';

    function updateHeaderStyle() {
      const scrolled = scrollViewport.scrollTop > 18 || window.scrollY > 18 || document.documentElement.scrollTop > 18;
      const stateKey = `${currentView}:${scrolled ? 1 : 0}`;

      if (stateKey !== lastHeaderStateKey) {
        lastHeaderStateKey = stateKey;
        const navGal = document.getElementById('nav-gallery');
        const navAbt = document.getElementById('nav-about');

        floatingHeader.classList.remove(
          'ds-header-hero',
          'ds-header-transparent-dark',
          'ds-header-frosted'
        );

        navGal.classList.toggle('is-active', currentView === 'gallery');
        navAbt.classList.toggle('is-active', currentView === 'about');
        const fGal = document.getElementById('foot-nav-gallery');
        const fAbt = document.getElementById('foot-nav-about');
        if (fGal) fGal.classList.toggle('is-active', currentView !== 'about');
        if (fAbt) fAbt.classList.toggle('is-active', currentView === 'about');

        const scrollCue = document.getElementById('hero-scroll-cue');
        if (scrollCue) scrollCue.classList.toggle('is-hidden', scrolled);
        const heroTech = document.getElementById('hero-tech-details');
        if (heroTech) heroTech.classList.toggle('is-hidden', scrolled);

        if (!scrolled) {
          if (currentView === 'gallery') {
            floatingHeader.classList.add('ds-header-hero');
          } else {
            floatingHeader.classList.add('ds-header-transparent-dark');
          }
        } else {
          floatingHeader.classList.add('ds-header-frosted');
        }
      }
    }

    function getVisibleViewportHeight() {
      const vv = window.visualViewport;
      if (vv && Math.abs(vv.scale - 1) <= 0.02 && vv.height > 0) {
        return vv.height;
      }
      return window.innerHeight;
    }

    function syncViewportHeight() {
      const vv = window.visualViewport;
      // Ignore pinch-zoom scaling so zooming a photograph never resizes the stage
      if (vv && Math.abs(vv.scale - 1) > 0.02) return;
      if (typeof isVisualizerOpen !== 'undefined' && isVisualizerOpen && typeof visualizerEl !== 'undefined' && visualizerEl) {
        const vh = getVisibleViewportHeight();
        const offsetTop = vv ? Math.max(0, vv.offsetTop) : 0;
        if (vh > 0) {
          visualizerEl.style.setProperty('--vis-viewport-height', `${Math.round(vh)}px`);
          visualizerEl.style.setProperty('--vis-viewport-offset-top', `${Math.round(offsetTop)}px`);
        }
        layoutVisualizerFit();
      }
    }

    scrollViewport.addEventListener('scroll', updateHeaderStyle, { passive: true });
    window.addEventListener('scroll', updateHeaderStyle, { passive: true });
    window.addEventListener('resize', syncViewportHeight, { passive: true });
    window.addEventListener('orientationchange', syncViewportHeight, { passive: true });
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', syncViewportHeight, { passive: true });
      window.visualViewport.addEventListener('scroll', syncViewportHeight, { passive: true });
    }

    const heroLandscapeIdx = PHOTOS.findIndex(p => p.id === CATALOG.site.heroPhotoId);
    const heroLandscape = heroLandscapeIdx !== -1 ? PHOTOS[heroLandscapeIdx] : PHOTOS[0];
    const heroPortrait = PHOTOS.find(p => p.orientation === 'portrait') || PHOTOS[1] || heroLandscape;

    function updateHeroForViewport() {
      const isMobile = window.innerWidth < 768;
      const activeHero = isMobile ? heroPortrait : heroLandscape;
      const heroTechEl = document.getElementById('hero-tech-details');
      if (heroTechEl && activeHero && activeHero.exif) {
        heroTechEl.innerHTML = `${activeHero.exif.focalLength} &middot; ${activeHero.exif.aperture} &middot; ${activeHero.exif.shutterSpeed} &middot; ${activeHero.exif.iso}`;
      }
    }
    window.addEventListener('resize', updateHeroForViewport);

    function toggleMobileMenu(open) {
      const overlay = document.getElementById('mobile-nav-overlay');
      const btn = document.getElementById('hdr-hamburger-btn');
      if (!overlay) return;
      const isOpen = open !== undefined ? open : !overlay.classList.contains('is-open');
      overlay.classList.toggle('is-open', isOpen);
      if (btn) btn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      document.body.style.overflow = isOpen ? 'hidden' : '';
    }

    function mobileNavTo(view) {
      toggleMobileMenu(false);
      showView(view);
    }

    function renderGallery() {
      const heroMobileSource = document.getElementById('hero-source-mobile');
      const heroFeaturedImg = document.getElementById('hero-featured-img');
      const mobileHeroUrl = heroPortrait.heroSrc || heroPortrait.src;
      const desktopHeroUrl = heroLandscape.heroSrc || heroLandscape.src;
      if (heroMobileSource && heroMobileSource.getAttribute('srcset') !== mobileHeroUrl) {
        heroMobileSource.srcset = mobileHeroUrl;
      }
      if (heroFeaturedImg && heroFeaturedImg.getAttribute('src') !== desktopHeroUrl) {
        heroFeaturedImg.src = desktopHeroUrl;
      }
      updateHeroForViewport();

      document.getElementById('gallery-intro-h1').textContent = CATALOG.site.introHeading;
      document.getElementById('gallery-intro-body').textContent = CATALOG.site.introDescription;

      const rowsMap = {};
      PHOTOS.forEach((p, idx) => {
        const r = p.row || 1;
        if (!rowsMap[r]) rowsMap[r] = [];
        rowsMap[r].push({ photo: p, idx });
      });

      const container = document.getElementById('gallery-rows-container');
      let html = '';
      Object.keys(rowsMap).sort((a, b) => Number(a) - Number(b)).forEach(rowKey => {
        const items = rowsMap[rowKey];
        const allPortraits = items.length === 4 && items.every(i => i.photo.orientation === 'portrait');
        if (allPortraits) {
          html += `<div class="grid grid-cols-2 sm:grid-cols-4 ds-gallery-row">`;
          items.forEach(({ photo, idx }) => {
            html += `
              <div onclick="openPhoto(${idx})" onmouseenter="warmPhoto(${idx})" ontouchstart="warmPhoto(${idx})" class="ds-thumb-card h-48 sm:h-56 md:h-64">
                <img src="${photo.thumbSrc || photo.src}" alt="${photo.title}" loading="lazy" decoding="async" />
              </div>
            `;
          });
          html += `</div>`;
        } else {
          html += `<div class="flex flex-col sm:flex-row ds-gallery-row">`;
          items.forEach(({ photo, idx }) => {
            html += `
              <div onclick="openPhoto(${idx})" onmouseenter="warmPhoto(${idx})" ontouchstart="warmPhoto(${idx})" style="flex: ${photo.aspectRatio} 1 0%;" class="ds-thumb-card h-48 sm:h-52 md:h-60">
                <img src="${photo.thumbSrc || photo.src}" alt="${photo.title}" loading="lazy" decoding="async" />
              </div>
            `;
          });
          html += `</div>`;
        }
      });
      container.innerHTML = html;

      document.getElementById('about-kicker').textContent = CATALOG.site.about.kicker;
      document.getElementById('about-heading').textContent = CATALOG.site.about.heading;
      document.getElementById('about-bio').textContent = CATALOG.site.about.bio;
      document.getElementById('about-specs').innerHTML = CATALOG.site.about.specs.map(s => `
        <div class="ds-spec-row">
          <span class="ds-label">${s.label}</span>
          <span class="ds-value">${s.value}</span>
        </div>
      `).join('');
    }

    // =========================================================================
    // ZERO-LAG PHOTO PRELOADING & DECODED BITMAP CACHE
    // Keeps all lightweight 1600px thumbnails decoded in memory + an LRU window
    // of 4 full-resolution masters so Next/Prev switches in 0ms without ever
    // leaving the previous photograph lingering on screen.
    // =========================================================================
    const detailStage = document.getElementById('view-detail');
    const detailImg = document.getElementById('detail-img');
    const decodedThumbCache = new Map();
    const decodedFullCache = new Map();
    const MAX_PINNED_FULL = 4;
    let detailLoadToken = 0;

    function _loadAndDecode(cacheMap, url, highPriority = false, maxEntries = 0) {
      if (!url) return Promise.resolve(false);
      if (cacheMap.has(url)) {
        const existing = cacheMap.get(url);
        if (maxEntries > 0) {
          cacheMap.delete(url);
          cacheMap.set(url, existing);
        }
        return existing.promise;
      }
      if (maxEntries > 0 && cacheMap.size >= maxEntries) {
        const oldestKey = cacheMap.keys().next().value;
        if (oldestKey !== undefined) cacheMap.delete(oldestKey);
      }
      const img = new Image();
      img.decoding = 'async';
      if (highPriority && 'fetchPriority' in img) {
        img.fetchPriority = 'high';
      }
      const entry = { img, ready: false, promise: null };
      entry.promise = new Promise((resolve) => {
        let settled = false;
        const finish = (ok) => {
          if (settled) return;
          settled = true;
          entry.ready = ok;
          resolve(ok);
        };
        const decodeNow = () => {
          if (typeof img.decode === 'function') {
            img.decode().then(() => finish(true)).catch(() => finish(img.naturalWidth > 0));
          } else {
            finish(true);
          }
        };
        img.onload = decodeNow;
        img.onerror = () => finish(false);
        img.src = url;
        if (img.complete && img.naturalWidth > 0) {
          decodeNow();
        }
      });
      cacheMap.set(url, entry);
      return entry.promise;
    }

    function preloadThumb(url, highPriority = false) {
      return _loadAndDecode(decodedThumbCache, url, highPriority, 0);
    }

    function preloadFull(url, highPriority = false) {
      return _loadAndDecode(decodedFullCache, url, highPriority, MAX_PINNED_FULL);
    }

    function warmPhoto(idx) {
      const p = PHOTOS[idx];
      if (!p) return;
      preloadThumb(p.thumbSrc || p.src, true);
      preloadFull(p.src, false);
    }

    function warmAllGalleryThumbsIdle() {
      let nextIdx = 0;
      const worker = () => {
        if (nextIdx >= PHOTOS.length) return;
        const p = PHOTOS[nextIdx++];
        preloadThumb(p.thumbSrc || p.src, false).finally(worker);
      };
      requestAnimationFrame(() => {
        setTimeout(() => {
          for (let c = 0; c < 3; c++) worker();
        }, 32);
      });
    }

    let savedGalleryScroll = null;

    function captureGalleryScroll() {
      if (currentView === 'gallery') {
        savedGalleryScroll = {
          windowY: window.scrollY || document.documentElement.scrollTop || 0,
          viewportTop: scrollViewport ? scrollViewport.scrollTop : 0
        };
      }
    }

    function navigateHash(target, mode = 'push') {
      if (window.location.hash === target) return true;
      try {
        if (mode === 'replace') {
          window.history.replaceState(window.history.state, '', target);
        } else {
          window.history.pushState(null, '', target);
        }
        return true;
      } catch (_) {
        window.location.hash = target;
        return false;
      }
    }

    const visualizerEl = document.getElementById('photo-visualizer');
    const visualizerImg = document.getElementById('visualizer-img');
    let visualizerLoadToken = 0;
    let visCurrentPhotoId = null;

    const VIS_MIN_SCALE = 1;
    const VIS_MAX_SCALE = 5;
    const VIS_TOGGLE_SCALE = 2.5;
    let visScale = 1;
    let visX = 0;
    let visY = 0;
    let visFitW = 0;
    let visFitH = 0;

    function getVisualizerViewport() {
      if (visualizerEl) {
        const rect = visualizerEl.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          return { vw: rect.width, vh: rect.height, left: rect.left, top: rect.top };
        }
      }
      const vw = window.innerWidth;
      const vh = window.visualViewport ? window.visualViewport.height : window.innerHeight;
      return { vw, vh, left: 0, top: 0 };
    }

    function clampVisualizerPan() {
      const { vw, vh } = getVisualizerViewport();
      if (visScale <= 1.001) {
        visScale = 1;
        visX = 0;
        visY = 0;
        return;
      }
      const maxX = Math.max(0, (visFitW * visScale - vw) / 2);
      const maxY = Math.max(0, (visFitH * visScale - vh) / 2);
      visX = Math.min(maxX, Math.max(-maxX, visX));
      visY = Math.min(maxY, Math.max(-maxY, visY));
    }

    function applyVisualizerTransform(animate = false) {
      if (!visualizerImg || !visualizerEl) return;
      clampVisualizerPan();
      visualizerImg.style.transition = animate
        ? 'transform 220ms cubic-bezier(0.22, 1, 0.36, 1)'
        : 'none';
      visualizerImg.style.transform = `translate3d(${visX}px, ${visY}px, 0) scale(${visScale})`;
      visualizerEl.classList.toggle('is-zoomed', visScale > 1.01);
    }

    function layoutVisualizerFit() {
      if (!visualizerImg || !visualizerEl) return;
      const { vw, vh } = getVisualizerViewport();
      const p = PHOTOS[currentIdx];
      let ratio = 1.5;
      if (visualizerImg.naturalWidth > 0 && visualizerImg.naturalHeight > 0) {
        ratio = visualizerImg.naturalWidth / visualizerImg.naturalHeight;
      } else if (p && p.aspectRatio > 0) {
        ratio = p.aspectRatio;
      }
      if (vw / vh > ratio) {
        visFitH = vh;
        visFitW = vh * ratio;
      } else {
        visFitW = vw;
        visFitH = vw / ratio;
      }
      visualizerImg.style.width = `${visFitW}px`;
      visualizerImg.style.height = `${visFitH}px`;
      applyVisualizerTransform(false);
    }

    function resetVisualizerZoom(animate = false) {
      visScale = 1;
      visX = 0;
      visY = 0;
      applyVisualizerTransform(animate);
    }

    function zoomVisualizerAt(targetScale, clientX, clientY, animate = false) {
      const nextScale = Math.min(VIS_MAX_SCALE, Math.max(VIS_MIN_SCALE, targetScale));
      const { vw, vh, left, top } = getVisualizerViewport();
      const cx = left + vw / 2;
      const cy = top + vh / 2;
      const dx = clientX - cx;
      const dy = clientY - cy;
      if (nextScale <= 1.001) {
        visScale = 1;
        visX = 0;
        visY = 0;
      } else {
        const scaleRatio = nextScale / visScale;
        visX = dx - (dx - visX) * scaleRatio;
        visY = dy - (dy - visY) * scaleRatio;
        visScale = nextScale;
      }
      applyVisualizerTransform(animate);
    }

    if (visualizerImg) {
      visualizerImg.addEventListener('load', () => {
        if (isVisualizerOpen) layoutVisualizerFit();
      });
    }
    window.addEventListener('resize', () => {
      if (isVisualizerOpen) layoutVisualizerFit();
    });
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', () => {
        if (isVisualizerOpen) layoutVisualizerFit();
      });
    }

    function syncVisualizerPhoto(p, resetZoom = false) {
      if (!p || !visualizerImg) return;
      const vToken = ++visualizerLoadToken;
      const isNewPhoto = visCurrentPhotoId !== p.id;
      visCurrentPhotoId = p.id;
      if (resetZoom || isNewPhoto) {
        visScale = 1;
        visX = 0;
        visY = 0;
      }

      const thumbUrl = p.thumbSrc || p.src;
      const fullUrl = p.src;
      const fullEntry = decodedFullCache.get(fullUrl);
      const thumbEntry = decodedThumbCache.get(thumbUrl);

      visualizerImg.alt = p.title;
      if (fullEntry && fullEntry.ready) {
        visualizerImg.style.opacity = '1';
        if (visualizerImg.getAttribute('src') !== fullUrl) {
          visualizerImg.src = fullUrl;
        }
      } else if (thumbEntry && thumbEntry.ready) {
        visualizerImg.style.opacity = '1';
        if (visualizerImg.getAttribute('src') !== thumbUrl) {
          visualizerImg.src = thumbUrl;
        }
        if (fullUrl !== thumbUrl) {
          preloadFull(fullUrl, true).then((ok) => {
            if (ok && isVisualizerOpen && visualizerLoadToken === vToken) {
              visualizerImg.src = fullUrl;
            }
          });
        }
      } else {
        visualizerImg.src = (detailImg && detailImg.getAttribute('src')) || thumbUrl;
        visualizerImg.style.opacity = '1';
        if (fullUrl !== visualizerImg.getAttribute('src')) {
          preloadFull(fullUrl, true).then((ok) => {
            if (ok && isVisualizerOpen && visualizerLoadToken === vToken) {
              visualizerImg.src = fullUrl;
            }
          });
        }
      }
      layoutVisualizerFit();
    }

    let visPushedHistory = false;
    let suppressNextVisPopstate = false;

    function setVisualizerThemeColor(active) {
      let meta = document.getElementById('vis-theme-color');
      if (active) {
        if (!meta) {
          meta = document.createElement('meta');
          meta.id = 'vis-theme-color';
          meta.name = 'theme-color';
          document.head.appendChild(meta);
        }
        meta.content = '#000000';
      } else if (meta) {
        meta.remove();
      }
    }

    function openVisualizer() {
      const p = PHOTOS[currentIdx];
      if (!p || !visualizerEl) return;
      isVisualizerOpen = true;
      visualizerEl.classList.add('is-open');
      visualizerEl.setAttribute('aria-hidden', 'false');
      setVisualizerThemeColor(true);
      syncViewportHeight();
      document.body.style.overflow = 'hidden';
      syncVisualizerPhoto(p, true);

      if (!visPushedHistory) {
        try {
          window.history.pushState({ visualizer: true }, '', window.location.hash || ('#/photo/' + p.id));
          visPushedHistory = true;
        } catch (_) {
          visPushedHistory = false;
        }
      }
    }

    function closeVisualizer(fromPopstate = false) {
      if (!isVisualizerOpen || !visualizerEl) return;
      isVisualizerOpen = false;
      visualizerEl.classList.remove('is-open', 'is-zoomed', 'is-dragging');
      visualizerEl.setAttribute('aria-hidden', 'true');
      setVisualizerThemeColor(false);
      document.body.style.overflow = '';
      resetVisualizerZoom(false);

      if (fromPopstate) {
        visPushedHistory = false;
      } else if (visPushedHistory) {
        visPushedHistory = false;
        if (window.history.state && window.history.state.visualizer) {
          suppressNextVisPopstate = true;
          try {
            window.history.back();
          } catch (_) {
            suppressNextVisPopstate = false;
          }
        }
      }
    }

    // Desktop Mouse / Wheel & Mobile Touch Zoom + Pan for Popup Visualizer
    if (visualizerEl) {
      let visPointerDown = false;
      let visDragMoved = 0;
      let visPointerStartX = 0;
      let visPointerStartY = 0;
      let visStartPanX = 0;
      let visStartPanY = 0;
      let visDownTarget = null;
      let visLastTouchTime = 0;

      visualizerEl.addEventListener('wheel', (e) => {
        if (!isVisualizerOpen) return;
        e.preventDefault();
        let delta = e.deltaY;
        if (e.deltaMode === 1) delta *= 16;
        else if (e.deltaMode === 2) delta *= 100;
        const sensitivity = e.ctrlKey ? 0.01 : 0.0022;
        const factor = Math.exp(-delta * sensitivity);
        zoomVisualizerAt(visScale * factor, e.clientX, e.clientY, false);
      }, { passive: false });

      visualizerEl.addEventListener('mousedown', (e) => {
        if (!isVisualizerOpen || e.button !== 0) return;
        if (Date.now() - visLastTouchTime < 500) return;
        if (e.target.closest('#visualizer-close-btn')) return;
        e.preventDefault();
        visPointerDown = true;
        visDragMoved = 0;
        visPointerStartX = e.clientX;
        visPointerStartY = e.clientY;
        visStartPanX = visX;
        visStartPanY = visY;
        visDownTarget = e.target;
        if (visScale > 1.01) {
          visualizerEl.classList.add('is-dragging');
        }
      });

      window.addEventListener('mousemove', (e) => {
        if (!visPointerDown || !isVisualizerOpen) return;
        const dx = e.clientX - visPointerStartX;
        const dy = e.clientY - visPointerStartY;
        visDragMoved = Math.hypot(dx, dy);
        if (visScale > 1.01 && visDragMoved > 2) {
          visX = visStartPanX + dx;
          visY = visStartPanY + dy;
          applyVisualizerTransform(false);
        }
      });

      window.addEventListener('mouseup', (e) => {
        if (!visPointerDown) return;
        visPointerDown = false;
        visualizerEl.classList.remove('is-dragging');
        if (!isVisualizerOpen) return;
        if (visDragMoved <= 5) {
          if (visDownTarget === visualizerImg) {
            const next = visScale > 1.05 ? 1 : VIS_TOGGLE_SCALE;
            zoomVisualizerAt(next, e.clientX, e.clientY, true);
          } else if (visDownTarget === visualizerEl) {
            closeVisualizer();
          }
        }
      });

      let visTouchMode = null;
      let visTouchMoved = 0;
      let visTouchStartX = 0;
      let visTouchStartY = 0;
      let visTouchLastX = 0;
      let visTouchLastY = 0;
      let visTouchStartTime = 0;
      let visSwipeActive = false;
      let visTouchTarget = null;
      let visPinchStartDist = 0;
      let visPinchStartScale = 1;
      let visPinchPrevMidX = 0;
      let visPinchPrevMidY = 0;
      let visLastTapTime = 0;
      let visLastTapX = 0;
      let visLastTapY = 0;

      visualizerEl.addEventListener('touchstart', (e) => {
        visLastTouchTime = Date.now();
        if (!isVisualizerOpen) return;
        if (e.target.closest('#visualizer-close-btn')) return;
        e.preventDefault();
        if (e.touches.length === 2) {
          const t0 = e.touches[0];
          const t1 = e.touches[1];
          visTouchMode = 'pinch';
          visTouchMoved = 999;
          visSwipeActive = false;
          visPinchStartDist = Math.hypot(t1.clientX - t0.clientX, t1.clientY - t0.clientY);
          visPinchStartScale = visScale;
          visPinchPrevMidX = (t0.clientX + t1.clientX) / 2;
          visPinchPrevMidY = (t0.clientY + t1.clientY) / 2;
        } else if (e.touches.length === 1) {
          const t0 = e.touches[0];
          visTouchMode = 'single';
          visTouchMoved = 0;
          visSwipeActive = false;
          visTouchStartX = t0.clientX;
          visTouchStartY = t0.clientY;
          visTouchLastX = t0.clientX;
          visTouchLastY = t0.clientY;
          visTouchStartTime = Date.now();
          visStartPanX = visX;
          visStartPanY = visY;
          visTouchTarget = e.target;
        }
      }, { passive: false });

      visualizerEl.addEventListener('touchmove', (e) => {
        visLastTouchTime = Date.now();
        if (!isVisualizerOpen) return;
        if (e.target.closest('#visualizer-close-btn')) return;
        e.preventDefault();
        if (e.touches.length === 2) {
          const t0 = e.touches[0];
          const t1 = e.touches[1];
          const dist = Math.hypot(t1.clientX - t0.clientX, t1.clientY - t0.clientY);
          const midX = (t0.clientX + t1.clientX) / 2;
          const midY = (t0.clientY + t1.clientY) / 2;
          if (visTouchMode !== 'pinch') {
            visTouchMode = 'pinch';
            visTouchMoved = 999;
            visSwipeActive = false;
            visPinchStartDist = dist;
            visPinchStartScale = visScale;
            visPinchPrevMidX = midX;
            visPinchPrevMidY = midY;
            return;
          }
          visX += (midX - visPinchPrevMidX);
          visY += (midY - visPinchPrevMidY);
          const targetScale = visPinchStartScale * (dist / Math.max(1, visPinchStartDist));
          zoomVisualizerAt(targetScale, midX, midY, false);
          visPinchPrevMidX = midX;
          visPinchPrevMidY = midY;
        } else if (e.touches.length === 1 && visTouchMode === 'single') {
          const t0 = e.touches[0];
          visTouchLastX = t0.clientX;
          visTouchLastY = t0.clientY;
          const dx = t0.clientX - visTouchStartX;
          const dy = t0.clientY - visTouchStartY;
          visTouchMoved = Math.hypot(dx, dy);
          if (visScale > 1.05 && visTouchMoved > 2) {
            visX = visStartPanX + dx;
            visY = visStartPanY + dy;
            applyVisualizerTransform(false);
          } else if (visScale <= 1.05 && (visSwipeActive || (Math.abs(dx) > Math.abs(dy) * 1.15 && Math.abs(dx) > 10))) {
            visSwipeActive = true;
            visX = dx * 0.35;
            visY = 0;
            applyVisualizerTransform(false);
          }
        }
      }, { passive: false });

      const onVisTouchEnd = (e) => {
        visLastTouchTime = Date.now();
        if (!isVisualizerOpen) return;
        if (e.target.closest('#visualizer-close-btn')) return;
        if (e.touches.length === 1) {
          const t0 = e.touches[0];
          visTouchMode = 'single';
          visTouchMoved = 999;
          visSwipeActive = false;
          visTouchStartX = t0.clientX;
          visTouchStartY = t0.clientY;
          visTouchLastX = t0.clientX;
          visTouchLastY = t0.clientY;
          visTouchStartTime = Date.now();
          visStartPanX = visX;
          visStartPanY = visY;
          return;
        }
        if (e.touches.length === 0) {
          if (visTouchMode === 'single') {
            const t = e.changedTouches && e.changedTouches[0];
            const endX = t ? t.clientX : visTouchLastX;
            const endY = t ? t.clientY : visTouchLastY;
            const dx = endX - visTouchStartX;
            const dy = endY - visTouchStartY;
            const duration = Date.now() - visTouchStartTime;

            if (visScale <= 1.05) {
              const isHorizontal = Math.abs(dx) > Math.abs(dy) * 1.15;
              const isQuickFlick = duration < 380 && Math.abs(dx) > 35;
              const isLongSwipe = Math.abs(dx) > 65;

              if (isHorizontal && (isQuickFlick || isLongSwipe)) {
                visX = 0;
                visY = 0;
                visSwipeActive = false;
                visTouchMode = null;
                stepPhoto(dx < 0 ? 1 : -1);
                return;
              }
              if (visSwipeActive) {
                visX = 0;
                visY = 0;
                applyVisualizerTransform(true);
              }
            }

            if (!visSwipeActive && visTouchMoved < 10 && t) {
              if (visTouchTarget === visualizerEl) {
                closeVisualizer();
              } else if (visTouchTarget === visualizerImg) {
                const now = Date.now();
                if (now - visLastTapTime < 300 && Math.hypot(t.clientX - visLastTapX, t.clientY - visLastTapY) < 32) {
                  visLastTapTime = 0;
                  const next = visScale > 1.05 ? 1 : VIS_TOGGLE_SCALE;
                  zoomVisualizerAt(next, t.clientX, t.clientY, true);
                } else {
                  visLastTapTime = now;
                  visLastTapX = t.clientX;
                  visLastTapY = t.clientY;
                }
              }
            }
          }
          visSwipeActive = false;
          visTouchMode = null;
        }
      };

      visualizerEl.addEventListener('touchend', onVisTouchEnd);
      visualizerEl.addEventListener('touchcancel', onVisTouchEnd);
    }

    function showView(view, push = true) {
      if (push && (view === 'gallery' || view === 'about')) {
        const target = '#/' + view;
        if (!navigateHash(target, 'push')) return;
      }
      _applyView(view);
    }

    function _applyView(view) {
      if (view !== 'detail' && isVisualizerOpen) {
        closeVisualizer();
      }
      if (floatingHeader) {
        floatingHeader.classList.add('is-switching-view');
      }
      const prevView = currentView;
      currentView = view;
      document.getElementById('view-gallery').classList.toggle('hidden', view !== 'gallery');
      document.getElementById('view-about').classList.toggle('hidden', view !== 'about');
      document.getElementById('view-detail').classList.toggle('hidden', view !== 'detail');

      const menuNav = document.getElementById('header-menu-nav');
      const photoTitleWrap = document.getElementById('hdr-photo-title-wrap');
      const mainNav = document.getElementById('header-main-nav');
      const statusNav = document.getElementById('header-photo-status');
      const leftBack = document.getElementById('hdr-left-back');
      const brandName = document.getElementById('hdr-brand-name');
      const hamburgerBtn = document.getElementById('hdr-hamburger-btn');
      const mobShowcaseBar = document.getElementById('mobile-showcase-bar');
      const mobSocialStack = document.getElementById('mobile-social-stack');
      floatingHeader.classList.toggle('is-detail', view === 'detail');
      if (mobSocialStack) mobSocialStack.classList.toggle('is-hidden', view !== 'gallery');

      if (view === 'detail') {
        menuNav.classList.add('is-hidden');
        photoTitleWrap.classList.remove('hidden');
        photoTitleWrap.classList.add('flex');
        mainNav.classList.add('hidden');
        brandName.classList.add('hidden');
        if (hamburgerBtn) hamburgerBtn.classList.add('hidden');
        leftBack.classList.remove('is-hidden');
        statusNav.classList.remove('is-hidden');
        if (mobShowcaseBar) mobShowcaseBar.classList.remove('hidden');
      } else {
        photoTitleWrap.classList.add('hidden');
        photoTitleWrap.classList.remove('flex');
        menuNav.classList.remove('is-hidden');
        mainNav.classList.remove('hidden');
        brandName.classList.remove('hidden');
        if (hamburgerBtn) hamburgerBtn.classList.remove('hidden');
        leftBack.classList.add('is-hidden');
        statusNav.classList.add('is-hidden');
        if (mobShowcaseBar) mobShowcaseBar.classList.add('hidden');
      }

      // Sync active state in mobile navigation drawer
      const mobGal = document.getElementById('mob-nav-gallery');
      const mobAbt = document.getElementById('mob-nav-about');
      if (mobGal) mobGal.classList.toggle('is-active', view === 'gallery');
      if (mobAbt) mobAbt.classList.toggle('is-active', view === 'about');

      const restoringGalleryScroll = view === 'gallery' && prevView === 'detail' && savedGalleryScroll !== null;
      if (restoringGalleryScroll) {
        const restoreTarget = savedGalleryScroll;
        savedGalleryScroll = null;
        scrollViewport.scrollTop = restoreTarget.viewportTop;
        window.scrollTo({ top: restoreTarget.windowY, behavior: 'instant' });
        requestAnimationFrame(() => {
          scrollViewport.scrollTop = restoreTarget.viewportTop;
          window.scrollTo({ top: restoreTarget.windowY, behavior: 'instant' });
          updateHeaderStyle();
          if (floatingHeader) {
            void floatingHeader.offsetHeight;
            floatingHeader.classList.remove('is-switching-view');
          }
        });
      } else {
        if (view !== 'detail') {
          savedGalleryScroll = null;
        }
        scrollViewport.scrollTop = 0;
        window.scrollTo({ top: 0, behavior: 'instant' });
      }

      updateHeaderStyle();
      if (floatingHeader && !restoringGalleryScroll) {
        void floatingHeader.offsetHeight;
        requestAnimationFrame(() => {
          floatingHeader.classList.remove('is-switching-view');
        });
      }
    }

    function openPhoto(idx, historyMode = 'push') {
      captureGalleryScroll();
      currentIdx = idx;
      const p = PHOTOS[idx];
      if (!p) return;
      if (historyMode) {
        const target = '#/photo/' + p.id;
        const mode = historyMode === 'replace' ? 'replace' : 'push';
        if (!navigateHash(target, mode)) return;
      }
      _applyOpenPhoto(idx);
    }

    function syncShowcaseTitlePadding() {
      const titleEl = document.getElementById('hdr-photo-title');
      if (!titleEl || !detailStage) return;
      const isMultiline = titleEl.offsetHeight > 38;
      detailStage.classList.toggle('is-multiline-title', isMultiline);
    }

    function _applyOpenPhoto(idx) {
      if (currentView === 'gallery' && savedGalleryScroll === null) {
        captureGalleryScroll();
      }
      currentIdx = idx;
      const p = PHOTOS[idx];
      if (!p) return;

      _applyView('detail');

      document.getElementById('hdr-photo-title').textContent = p.title;
      syncShowcaseTitlePadding();
      document.getElementById('hdr-photo-counter').textContent = `${idx + 1} of ${PHOTOS.length}`;
      const mobCounter = document.getElementById('mob-photo-counter');
      if (mobCounter) mobCounter.textContent = `${idx + 1} of ${PHOTOS.length}`;

      const token = ++detailLoadToken;
      const thumbUrl = p.thumbSrc || p.src;
      const showcaseUrl = p.showcaseSrc || p.src;
      const fullEntry = decodedFullCache.get(showcaseUrl);
      const thumbEntry = decodedThumbCache.get(thumbUrl);

      if (detailImg) {
        detailImg.style.transition = 'none';
        detailImg.style.transform = 'translateX(0)';
        detailImg.alt = p.title;

        if (fullEntry && fullEntry.ready) {
          detailImg.style.opacity = '1';
          if (detailImg.getAttribute('src') !== showcaseUrl) {
            detailImg.src = showcaseUrl;
          }
          detailImg.dataset.photoId = p.id;
        } else if (thumbEntry && thumbEntry.ready) {
          detailImg.style.opacity = '1';
          if (detailImg.getAttribute('src') !== thumbUrl) {
            detailImg.src = thumbUrl;
          }
          detailImg.dataset.photoId = p.id;
          if (showcaseUrl !== thumbUrl) {
            preloadFull(showcaseUrl, true).then((ok) => {
              if (ok && detailLoadToken === token) {
                detailImg.src = showcaseUrl;
              }
            });
          }
        } else {
          // Cold cache miss: clear previous bitmap immediately so old photo never lingers
          if (detailImg.dataset.photoId !== p.id) {
            detailImg.style.opacity = '0';
            detailImg.removeAttribute('src');
            detailImg.dataset.photoId = p.id;
          }
          preloadThumb(thumbUrl, true).then((ok) => {
            if (detailLoadToken !== token) return;
            if (ok && detailImg.getAttribute('src') !== showcaseUrl) {
              detailImg.src = thumbUrl;
              detailImg.style.opacity = '1';
            }
            if (showcaseUrl !== thumbUrl) {
              preloadFull(showcaseUrl, true).then((fullOk) => {
                if (fullOk && detailLoadToken === token) {
                  detailImg.src = showcaseUrl;
                  detailImg.style.opacity = '1';
                }
              });
            } else if (!ok) {
              detailImg.src = showcaseUrl;
              detailImg.style.opacity = '1';
            }
          });
        }
      }

      if (isVisualizerOpen) {
        syncVisualizerPhoto(p);
      }

      // Preload & decode adjacent Prev / Next photos so stepping is instantaneous
      const nextIdx = (idx + 1) % PHOTOS.length;
      const prevIdx = (idx - 1 + PHOTOS.length) % PHOTOS.length;
      preloadThumb(PHOTOS[nextIdx].thumbSrc || PHOTOS[nextIdx].src, true);
      preloadThumb(PHOTOS[prevIdx].thumbSrc || PHOTOS[prevIdx].src, true);
      preloadFull(PHOTOS[nextIdx].showcaseSrc || PHOTOS[nextIdx].src, false);
      preloadFull(PHOTOS[prevIdx].showcaseSrc || PHOTOS[prevIdx].src, false);
      if (isVisualizerOpen) {
        preloadFull(PHOTOS[nextIdx].src, false);
        preloadFull(PHOTOS[prevIdx].src, false);
      }

      const specRows = [
        { label: 'LOCATION & YEAR', value: p.location },
        { label: 'FOCAL LENGTH', value: p.exif.focalLength },
        { label: 'APERTURE', value: p.exif.aperture },
        { label: 'SHUTTER SPEED', value: p.exif.shutterSpeed },
        { label: 'ISO', value: p.exif.iso }
      ];
      document.getElementById('detail-spec-table').innerHTML = specRows.map(r => `
        <div class="ds-spec-row">
          <span class="ds-label">${r.label}</span>
          <span class="ds-value">${r.value}</span>
        </div>
      `).join('');

      document.getElementById('dt-desc').textContent = p.description;

      const showPrint = printShopPreview || (p.print && p.print.enabled);
      const printHook = document.getElementById('detail-print-hook');
      printHook.classList.toggle('hidden', !showPrint);
      if (showPrint && p.print) {
        document.getElementById('detail-print-meta').textContent = `${p.print.dimensions} · ${p.print.price}`;
        document.getElementById('detail-print-btn').innerHTML = `<span>Order print · ${p.print.price}</span>`;
      }
    }

    function handleRoute() {
      if (suppressNextVisPopstate) {
        suppressNextVisPopstate = false;
        const curPhoto = PHOTOS[currentIdx];
        if (currentView === 'detail' && curPhoto) {
          navigateHash('#/photo/' + curPhoto.id, 'replace');
        }
        return;
      }
      if (isVisualizerOpen && !(window.history.state && window.history.state.visualizer)) {
        closeVisualizer(true);
        const curPhoto = PHOTOS[currentIdx];
        if (currentView === 'detail' && curPhoto) {
          navigateHash('#/photo/' + curPhoto.id, 'replace');
          return;
        }
      }
      const hash = window.location.hash || '';
      if (hash.startsWith('#/photo/')) {
        const slug = hash.replace('#/photo/', '').trim();
        const idx = PHOTOS.findIndex(p => p.id === slug);
        if (idx !== -1) {
          _applyOpenPhoto(idx);
          return;
        }
      }
      if (hash === '#/about') {
        _applyView('about');
        return;
      }
      _applyView('gallery');
    }

    window.addEventListener('hashchange', handleRoute);
    window.addEventListener('popstate', handleRoute);

    function stepPhoto(dir) {
      const next = (currentIdx + dir + PHOTOS.length) % PHOTOS.length;
      openPhoto(next, 'replace');
    }

    // Touch Swiping in Showcase View & Mobile Tap-to-Fullscreen
    let touchStartX = 0;
    let touchStartY = 0;
    let touchCurrentX = 0;
    let touchStartTime = 0;
    let isTouchSwiping = false;
    let detailJustSwiped = false;

    if (detailStage) {
      detailStage.addEventListener('touchstart', (e) => {
        if (currentView !== 'detail' || isVisualizerOpen || e.touches.length !== 1) return;
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
        touchCurrentX = touchStartX;
        touchStartTime = Date.now();
        isTouchSwiping = true;
        if (detailImg) detailImg.style.transition = 'none';
      }, { passive: true });

      detailStage.addEventListener('touchmove', (e) => {
        if (!isTouchSwiping || currentView !== 'detail') return;
        touchCurrentX = e.touches[0].clientX;
        const deltaX = touchCurrentX - touchStartX;
        const deltaY = e.touches[0].clientY - touchStartY;

        // Provide elastic horizontal feedback when dragging
        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
          if (detailImg) {
            detailImg.style.transform = `translateX(${deltaX * 0.35}px)`;
          }
        }
      }, { passive: true });

      detailStage.addEventListener('touchend', (e) => {
        if (!isTouchSwiping || currentView !== 'detail') return;
        isTouchSwiping = false;
        const deltaX = touchCurrentX - touchStartX;
        const deltaY = (e.changedTouches[0] ? e.changedTouches[0].clientY : touchStartY) - touchStartY;
        const duration = Date.now() - touchStartTime;

        if (Math.abs(deltaX) > 10) {
          detailJustSwiped = true;
          setTimeout(() => { detailJustSwiped = false; }, 80);
        }

        if (detailImg) {
          detailImg.style.transition = 'transform 220ms cubic-bezier(0.22, 1, 0.36, 1)';
          detailImg.style.transform = 'translateX(0)';
        }

        const isHorizontal = Math.abs(deltaX) > Math.abs(deltaY) * 1.15;
        const isQuickFlick = duration < 380 && Math.abs(deltaX) > 35;
        const isLongSwipe = Math.abs(deltaX) > 65;

        if (isHorizontal && (isQuickFlick || isLongSwipe)) {
          if (deltaX < 0) {
            stepPhoto(1);  // Swipe Left -> Next Photo
          } else {
            stepPhoto(-1); // Swipe Right -> Previous Photo
          }
        }
      }, { passive: true });
    }

    if (detailImg) {
      detailImg.addEventListener('click', () => {
        if (window.innerWidth < 768 && !isVisualizerOpen && !detailJustSwiped) {
          openVisualizer();
        }
      });
    }

    // Keyboard Navigation for Desktop Showcase & Zoomable Popup Visualizer
    window.addEventListener('keydown', (e) => {
      if (isVisualizerOpen) {
        if (e.key === 'Escape') {
          e.preventDefault();
          closeVisualizer();
          return;
        }
        const { vw, vh, left, top } = getVisualizerViewport();
        const cx = left + vw / 2;
        const cy = top + vh / 2;
        if (e.key === '+' || e.key === '=') {
          e.preventDefault();
          zoomVisualizerAt(visScale * 1.4, cx, cy, true);
          return;
        }
        if (e.key === '-' || e.key === '_') {
          e.preventDefault();
          zoomVisualizerAt(visScale / 1.4, cx, cy, true);
          return;
        }
        if (e.key === '0') {
          e.preventDefault();
          resetVisualizerZoom(true);
          return;
        }
      }
      if (currentView === 'detail') {
        if (e.key === 'ArrowRight' || e.key === 'Right') {
          stepPhoto(1);
        } else if (e.key === 'ArrowLeft' || e.key === 'Left') {
          stepPhoto(-1);
        } else if (e.key === 'Escape') {
          showView('gallery');
        }
      }
    });

    function switchMode(mode) {
      const isDS = mode === 'design-system';
      document.getElementById('scroll-viewport').classList.toggle('hidden', isDS);
      document.getElementById('design-system-viewport').classList.toggle('hidden', !isDS);

      const btnWeb = document.getElementById('mode-btn-website');
      const btnDS = document.getElementById('mode-btn-ds');
      if (isDS) {
        btnDS.className = "px-2.5 py-1 rounded-md text-xs font-medium transition-colors bg-[var(--primary)] text-[var(--primary-foreground)]";
        btnWeb.className = "px-2.5 py-1 rounded-md text-xs font-medium transition-colors bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:opacity-90";
      } else {
        btnWeb.className = "px-2.5 py-1 rounded-md text-xs font-medium transition-colors bg-[var(--primary)] text-[var(--primary-foreground)]";
        btnDS.className = "px-2.5 py-1 rounded-md text-xs font-medium transition-colors bg-[var(--secondary)] text-[var(--secondary-foreground)] hover:opacity-90";
      }
    }

    function togglePrintShop(enabled) {
      printShopPreview = enabled;
      if (currentView === 'detail') {
        openPhoto(currentIdx, 'replace');
      } else {
        switchMode('website');
        openPhoto(currentIdx, 'push');
      }
    }

    function triggerPrintOrder(btn) {
      const prev = btn.innerHTML;
      btn.innerHTML = "<span>✓ Redirecting to print partner...</span>";
      setTimeout(() => { btn.innerHTML = prev; }, 1400);
    }

    renderGallery();
    warmAllGalleryThumbsIdle();
    if (window.location.hash && window.location.hash !== '#/' && window.location.hash !== '#/gallery') {
      handleRoute();
    } else {
      updateHeaderStyle();
    }
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Alejandro Oropeza Photo Gallery")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("build", help="Compile Design System CSS and photos.json into the website")

    add_p = sub.add_parser("add", help="Add a new photograph with automatic EXIF extraction")
    add_p.add_argument("photo_path", help="Path to the .jpg file")
    add_p.add_argument("--title", required=True, help="Photograph title")
    add_p.add_argument("--location", required=True, help="Location & year (e.g., 'London, UK · 2026')")
    add_p.add_argument("--description", required=True, help="Photograph description")
    add_p.add_argument("--row", type=int, default=3, help="Gallery row number")
    add_p.add_argument("--focal", help="Override Focal Length")
    add_p.add_argument("--aperture", help="Override Aperture")
    add_p.add_argument("--shutter", help="Override Shutter Speed")
    add_p.add_argument("--iso", help="Override ISO")
    add_p.add_argument("--price", default="$240", help="Print price when print shop is enabled")

    parsed = parser.parse_args()
    if parsed.cmd == "add":
        cmd_add(parsed)
    else:
        cmd_build(parsed)
