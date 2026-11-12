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

PROD_EXTRA_HEAD = """  <link rel="icon" type="image/svg+xml" href="favicon.svg" />
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
    "arrow-left": '<svg width="16" height="16" class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>',
    "arrow-right": '<svg width="16" height="16" class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
    "menu": '<svg width="16" height="16" class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/></svg>',
    "close": '<svg width="16" height="16" class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
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
        "Back to gallery",
        icon_left="arrow-left",
        onclick="showView('gallery')",
        elem_id="hdr-left-back",
        extra_cls="ds-showcase-back is-hidden",
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

    # Top Header Pill Instance
    top_header_pill = render_pill(
        left_html=(
            '<button onclick="showView(\'gallery\')" id="hdr-brand-name" '
            'class="ds-brand-name text-left hover:opacity-75 transition-opacity focus:outline-none">'
            "Alejandro Oropeza</button>" + btn_hdr_back
        ),
        center_html=(
            '<nav id="header-menu-nav" class="ds-menu-nav">'
            '<button onclick="showView(\'gallery\')" onmousemove="trackMenuLight(event, this)" id="nav-gallery" class="ds-menu-link is-active focus:outline-none"><span class="ds-menu-text">GALLERY</span></button>'
            '<span class="ds-menu-sep">/</span>'
            '<button onclick="showView(\'about\')" onmousemove="trackMenuLight(event, this)" id="nav-about" class="ds-menu-link focus:outline-none"><span class="ds-menu-text">ABOUT ME</span></button>'
            "</nav>"
            '<div id="hdr-photo-title-wrap" class="hidden flex-col items-center justify-center text-center pointer-events-none px-2 max-w-[calc(100vw-2rem)] md:max-w-none">'
            '<span id="hdr-photo-title" class="ds-h2"></span>'
            '<span id="hdr-showcase-author">Alejandro Oropeza</span>'
            "</div>"
        ),
        right_html=(
            f'<div id="header-main-nav" class="flex items-center justify-end gap-2 sm:gap-2.5">{ibtn_hdr_ig}{ibtn_hdr_500px}{ibtn_hdr_menu}</div>'
            f'<div id="header-photo-status" class="ds-showcase-status is-hidden items-center justify-end gap-2.5">'
            f'<span id="hdr-photo-counter" class="whitespace-nowrap">1 of 10</span>'
            f'<div class="flex items-center gap-1.5">{ibtn_hdr_prev}{ibtn_hdr_next}</div>'
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
        right_html=f'<div class="flex items-center gap-1.5">{ibtn_mob_prev}{ibtn_mob_next}</div>',
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
        right_html=f'<div class="flex items-center gap-1.5">{ds_ibtn_prev}{ds_ibtn_next}</div>',
        controls_inset=True,
        extra_cls="mx-auto w-full max-w-[23rem]",
    )

    return {
        # Standardized Pill Instances
        "__PILL_TOP_HEADER__": top_header_pill,
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
        "hidden w-full max-h-[450px] overflow-y-auto rounded-b-xl p-5 space-y-6"
        if is_inline_embed
        else "hidden max-w-5xl mx-auto px-6 sm:px-10 py-12 space-y-8"
    )
    header_pos_cls = "sticky top-0 left-0 right-0 z-50 px-4 sm:px-6" if is_inline_embed else "fixed top-0 left-0 right-0 z-50 px-4 sm:px-10"
    main_pull_cls = "-mt-[4.5rem]" if is_inline_embed else ""

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

    hero_landscape = next(
        (p for p in catalog["photos"] if p["id"] == catalog["site"].get("heroPhotoId")),
        catalog["photos"][0],
    )
    hero_portrait = next(
        (p for p in catalog["photos"] if p.get("orientation") == "portrait"),
        hero_landscape,
    )

    html = HTML_BASE_TEMPLATE
    for token, rendered in build_button_instances(catalog).items():
        html = html.replace(token, rendered)
    html = html.replace("/* __DESIGN_SYSTEM_CSS__ */", design_system_css)
    html = html.replace("__CATALOG_JSON__", json.dumps(catalog, ensure_ascii=False))
    html = html.replace("__HERO_MOBILE_SRCSET__", hero_portrait.get("src", ""))
    html = html.replace("__HERO_DESKTOP_SRC__", hero_landscape.get("src", ""))
    html = html.replace("__HERO_HEIGHT_CLS__", hero_height_cls)
    html = html.replace("__STAGE_HEIGHT_CLS__", stage_height_cls)
    html = html.replace("__SHELL_CLS__", shell_cls)
    html = html.replace("__DS_SHELL_CLS__", ds_shell_cls)
    html = html.replace("__HEADER_POS_CLS__", header_pos_cls)
    html = html.replace("__MAIN_PULL_CLS__", main_pull_cls)
    html = html.replace("__BODY_CLS__", body_cls)
    html = html.replace("__SHELL_STYLE__", shell_style)
    html = html.replace("<!-- __MODE_SWITCHER_BAR__ -->", mode_switcher_bar)
    html = html.replace("<!-- __EXTRA_HEAD__ -->", extra_head)
    return html


def build_production(design_system_css: str, catalog: dict):
    dist_dir = ROOT_DIR / "dist"
    dist_photos_dir = dist_dir / "photos"
    dist_thumbs_dir = dist_photos_dir / "thumbs"
    dist_thumbs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy untouched full-resolution originals to dist/photos/ & generate 1600px Lanczos gallery thumbnails
    for p in catalog["photos"]:
        fname = p["file"]
        src = PUBLIC_PHOTOS_DIR / "hi-res" / fname
        if not src.exists():
            src = PUBLIC_PHOTOS_DIR / fname
        shutil.copy2(src, dist_photos_dir / fname)

        im = Image.open(src)
        icc = im.info.get("icc_profile")
        thumb_im = im.copy()
        if max(thumb_im.size) > 1600:
            thumb_im.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        save_kwargs = {"format": "JPEG", "quality": 90, "optimize": True}
        if icc:
            save_kwargs["icc_profile"] = icc
        thumb_im.save(dist_thumbs_dir / fname, **save_kwargs)

    # 2. Build production catalog with relative full-res & thumbnail paths (zero base64 overhead!)
    prod_catalog = json.loads(json.dumps(catalog))
    for p in prod_catalog["photos"]:
        p["src"] = f"photos/{p['file']}"
        p["thumbSrc"] = f"photos/thumbs/{p['file']}"

    # 3. Build dist/index.html (clean live site without dev bar, ~38KB initial HTML)
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
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Alejandro Oropeza — Photo gallery</title>
  <meta name="description" content="Alejandro Oropeza — Travel photography studying architecture, wildlife, coastlines, and solitary figures in quiet isolation." />
  <!-- __EXTRA_HEAD__ -->
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
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
        <div class="absolute inset-x-0 top-0 h-28 pointer-events-none" style="background: linear-gradient(to bottom, rgba(0,0,0,0.52) 0%, rgba(0,0,0,0) 100%);"></div>
        <div class="absolute inset-x-0 bottom-0 h-24 pointer-events-none" style="background: linear-gradient(to top, rgba(0,0,0,0.48) 0%, rgba(0,0,0,0) 100%);">
          <!-- Technical details (bottom-right) -->
          <span id="hero-tech-details" class="ds-hero-tech absolute right-4 sm:right-6 bottom-4 text-right"></span>
          <!-- Scroll signifier (bottom-center): label + softly bobbing arrow -->
          <button type="button" id="hero-scroll-cue" onclick="scrollPastHero()" class="ds-scroll-cue absolute left-1/2 -translate-x-1/2 bottom-3 pointer-events-auto focus:outline-none" aria-label="View gallery">
            <span class="ds-scroll-cue-label">View gallery</span>
            <svg class="ds-scroll-cue-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          </button>
        </div>
      </section>

      <!-- Gallery Grid Section -->
      <div class="px-4 sm:px-6 pt-8 pb-16">
        <div class="max-w-2xl mb-5">
          <h1 id="gallery-intro-h1" class="ds-h1">Explore the gallery</h1>
          <p id="gallery-intro-body" class="ds-body mt-1"></p>
        </div>
        <div id="gallery-rows-container" class="space-y-2.5"></div>
      </div>

    </main>

    <!-- VIEW 2: PHOTO SHOWCASE PAGE -->
    <section id="view-detail" class="hidden __MAIN_PULL_CLS__">
      
      <!-- Dynamic-Viewport-Height Pure White Photo Stage (.ds-showcase-stage) -->
      <div class="ds-showcase-stage relative w-full __STAGE_HEIGHT_CLS__ flex items-center justify-center overflow-hidden">
        <div class="w-full h-full flex items-center justify-center">
          <img id="detail-img" alt="Selected Photograph" class="max-h-full max-w-full object-contain shadow-sm mx-auto block" />
        </div>
      </div>

      <!-- Pure Neutral Grey Spec Sheet & Description Band Below Stage (.ds-showcase-details) -->
      <div class="ds-showcase-details">
        <div class="max-w-md mx-auto px-4 py-8">
          <div class="text-center">
            <h2 class="ds-h3">Photo details</h2>
          </div>

          <div id="detail-spec-table" class="mt-3"></div>

          <!-- Optional Print Shop Hook (Uses Tonal Master Button .ds-btn) -->
          <div id="detail-print-hook" class="hidden mt-4 pt-3 flex items-center justify-between" style="border-top: 1px solid var(--ds-color-border-strong);">
            <div>
              <span class="ds-label block">ARCHIVAL PRINT</span>
              <span id="detail-print-meta" class="ds-value">16 × 24 in · $240</span>
            </div>
            __BTN_PRINT_ORDER__
          </div>

          <!-- Centered DESCRIPTION (.ds-h3 + .ds-body) -->
          <div class="mt-5 pb-20 md:pb-4">
            <h3 class="ds-h3 text-center">DESCRIPTION</h3>
            <p id="dt-desc" class="ds-body mt-1.5 text-center"></p>
          </div>
        </div>
      </div>

      <!-- FLOATING BOTTOM SHOWCASE CONTROLS (Mobile Only — Standardized .ds-pill Instance) -->
      __PILL_MOB_SHOWCASE__

    </section>

    <!-- VIEW 3: ABOUT ME PAGE -->
    <section id="view-about" class="hidden __MAIN_PULL_CLS__ pt-24 px-4 sm:px-6 pb-16 max-w-xl mx-auto">
      <span id="about-kicker" class="ds-label block">ABOUT ME</span>
      <h1 id="about-heading" class="ds-brand-name mt-1">Alejandro Oropeza</h1>
      <p id="about-bio" class="ds-body mt-2.5"></p>
      <div id="about-specs" class="mt-4 pt-2" style="border-top: 1px solid var(--ds-color-border);"></div>
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
      <h2 class="ds-h3 mb-2.5">1. Unified Component System (Tonal &amp; Surface Buttons · Standardized Pill · 48px M / 40px D)</h2>
      <div class="space-y-4 rounded-lg p-4" style="background-color: var(--ds-color-subtle); border: 1px solid var(--ds-color-border);">
        
        <!-- TONAL BUTTON (.ds-btn) -->
        <div class="pb-3.5" style="border-bottom: 1px solid var(--ds-color-border);">
          <div class="flex flex-wrap items-baseline justify-between gap-2 mb-2.5">
            <span class="ds-value font-medium">Tonal Button (<code>.ds-btn</code> · <code>render_button()</code>)</span>
            <span class="ds-label">Mobile: 48px high (12px side padding) · Desktop: 40px high (16px side padding) · Optional icon toggle</span>
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
            <span class="ds-label">Mobile: 48px × 48px circle · Desktop: 40px × 40px circle · Shared hover light &amp; press physics</span>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            __DS_IBTN_PREV__
            __DS_IBTN_NEXT__
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

        <!-- SITE FOOTER SPECIMEN -->
        <div class="pt-3 space-y-2.5" style="border-top: 1px solid var(--ds-color-border);">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <span class="ds-value font-medium">Site Footer (<code>.ds-footer</code>)</span>
            <span class="ds-label">Mirror of the Top Bar · Wordmark · Menu · Tonal IconButtons · Thin rule above · Muted ©</span>
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
      <h2 class="ds-h3 mb-2.5">2. Typography Hierarchy (Futura Non-Bold + Avenir)</h2>
      <div class="space-y-2.5 rounded-lg p-3.5" style="background-color: var(--ds-color-subtle); border: 1px solid var(--ds-color-border);">
        <div class="ds-spec-row">
          <div>
            <span class="ds-label block">.ds-h1 · Futura Light (300) · Uppercase · +0.04em</span>
            <span class="ds-h1 mt-0.5 block">Explore the gallery</span>
          </div>
          <code class="text-xs text-neutral-500">26px M · 30px D / 300</code>
        </div>
        <div class="ds-spec-row">
          <div>
            <span class="ds-label block">.ds-h2 · Futura Regular (400) · Uppercase · +0.05em</span>
            <span class="ds-h2 mt-0.5 block">Perch Rock Lighthouse</span>
          </div>
          <code class="text-xs text-neutral-500">20px M · 24px D / 400</code>
        </div>
        <div class="ds-spec-row">
          <div>
            <span class="ds-label block">.ds-h3 · Futura Regular (400) · Uppercase · +0.12em</span>
            <span class="ds-h3 mt-0.5 block">PHOTO DETAILS / DESCRIPTION</span>
          </div>
          <code class="text-xs text-neutral-500">14px M · 15px D / 400</code>
        </div>
        <div class="ds-spec-row">
          <div>
            <span class="ds-label block">.ds-brand-name · Avenir Medium (500) · +0.02em · Center-Aligned</span>
            <span class="ds-brand-name mt-0.5 block">Alejandro Oropeza</span>
          </div>
          <code class="text-xs text-neutral-500">18px / 500</code>
        </div>
        <div class="ds-spec-row" style="border-bottom: none;">
          <div>
            <span class="ds-label block">.ds-body (16px) / .ds-value (15px) / .ds-label (12px) · Avenir</span>
            <span class="ds-body mt-0.5 block">Travel photography studying subjects in quiet isolation.</span>
          </div>
          <code class="text-xs text-neutral-500">16px / 300–400</code>
        </div>
      </div>
    </div>

    <!-- 3. PURE MONOCHROME COLOR TOKENS -->
    <div>
      <h2 class="ds-h3 mb-2.5">3. Pure Neutral Monochrome Tokens (R = G = B)</h2>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div class="p-2.5 rounded border" style="background-color: #FFFFFF; border-color: #EBEBEB;">
          <div class="ds-value">#FFFFFF</div>
          <div class="ds-label mt-0.5">--ds-color-canvas</div>
        </div>
        <div class="p-2.5 rounded border" style="background-color: #F2F2F2; border-color: #E5E5E5;">
          <div class="ds-value">#F2F2F2</div>
          <div class="ds-label mt-0.5">--ds-color-stage</div>
        </div>
        <div class="p-2.5 rounded border" style="background-color: #525252; border-color: #525252; color: #FFFFFF;">
          <div class="ds-value" style="color: #FFFFFF;">#525252</div>
          <div class="ds-label mt-0.5" style="color: #D4D4D4;">--ds-color-ink-secondary</div>
        </div>
        <div class="p-2.5 rounded border" style="background-color: #141414; border-color: #141414; color: #FFFFFF;">
          <div class="ds-value" style="color: #FFFFFF;">#141414</div>
          <div class="ds-label mt-0.5" style="color: #A3A3A3;">--ds-color-ink-primary</div>
        </div>
      </div>
    </div>

  </div>

  <script>
    const CATALOG = __CATALOG_JSON__;
    const PHOTOS = CATALOG.photos;

    let currentIdx = 0;
    let currentView = 'gallery';
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

    function updateHeaderStyle() {
      const scrolled = scrollViewport.scrollTop > 18 || window.scrollY > 18 || document.documentElement.scrollTop > 18;
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

      if (!scrolled) {
        if (currentView === 'gallery') {
          floatingHeader.classList.add('ds-header-hero');
        } else {
          floatingHeader.classList.add('ds-header-transparent-dark');
        }
      } else {
        floatingHeader.classList.add('ds-header-frosted');
      }

      if (currentView === 'detail' && window.innerWidth < 768) {
        updateMobileDockPosition();
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
      const vh = getVisibleViewportHeight();
      if (vh > 0) {
        document.documentElement.style.setProperty('--app-viewport-height', `${Math.round(vh)}px`);
      }
      if (currentView === 'detail' && window.innerWidth < 768) {
        updateMobileDockPosition();
      }
    }

    function updateMobileDockPosition() {
      const dock = document.getElementById('mobile-showcase-bar');
      const footer = document.getElementById('site-footer');
      if (!dock || !footer || currentView !== 'detail') return;
      if (window.innerWidth >= 768) {
        dock.style.transform = '';
        return;
      }
      const footerRect = footer.getBoundingClientRect();
      const windowHeight = getVisibleViewportHeight();
      const baseBottom = 18;
      const clearance = 16;
      const threshold = windowHeight - baseBottom;
      if (footerRect.top < threshold + clearance) {
        const pushUp = (threshold + clearance) - footerRect.top;
        dock.style.transform = `translateX(-50%) translateY(-${pushUp}px)`;
      } else {
        dock.style.transform = 'translateX(-50%) translateY(0)';
      }
    }

    syncViewportHeight();
    scrollViewport.addEventListener('scroll', updateHeaderStyle, { passive: true });
    window.addEventListener('scroll', updateHeaderStyle, { passive: true });
    window.addEventListener('resize', syncViewportHeight, { passive: true });
    window.addEventListener('orientationchange', syncViewportHeight, { passive: true });
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', syncViewportHeight, { passive: true });
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
      if (heroMobileSource && heroMobileSource.getAttribute('srcset') !== heroPortrait.src) {
        heroMobileSource.srcset = heroPortrait.src;
      }
      if (heroFeaturedImg && heroFeaturedImg.getAttribute('src') !== heroLandscape.src) {
        heroFeaturedImg.src = heroLandscape.src;
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
          html += `<div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5">`;
          items.forEach(({ photo, idx }) => {
            html += `
              <div onclick="openPhoto(${idx})" class="ds-thumb-card h-48 sm:h-56">
                <img src="${photo.thumbSrc || photo.src}" alt="${photo.title}" loading="lazy" decoding="async" />
              </div>
            `;
          });
          html += `</div>`;
        } else {
          html += `<div class="flex flex-col sm:flex-row gap-2.5">`;
          items.forEach(({ photo, idx }) => {
            html += `
              <div onclick="openPhoto(${idx})" style="flex: ${photo.aspectRatio} 1 0%;" class="ds-thumb-card h-44 sm:h-52">
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

    let savedGalleryScroll = null;

    function captureGalleryScroll() {
      if (currentView === 'gallery') {
        savedGalleryScroll = {
          windowY: window.scrollY || document.documentElement.scrollTop || 0,
          viewportTop: scrollViewport ? scrollViewport.scrollTop : 0
        };
      }
    }

    function showView(view, push = true) {
      if (push && (view === 'gallery' || view === 'about')) {
        const target = '#/' + view;
        if (window.location.hash !== target) {
          window.location.hash = target;
          return;
        }
      }
      _applyView(view);
    }

    function _applyView(view) {
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
      floatingHeader.classList.toggle('is-detail', view === 'detail');

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

      if (view === 'gallery' && prevView === 'detail' && savedGalleryScroll !== null) {
        const restoreTarget = savedGalleryScroll;
        savedGalleryScroll = null;
        scrollViewport.scrollTop = restoreTarget.viewportTop;
        window.scrollTo({ top: restoreTarget.windowY, behavior: 'instant' });
        requestAnimationFrame(() => {
          scrollViewport.scrollTop = restoreTarget.viewportTop;
          window.scrollTo({ top: restoreTarget.windowY, behavior: 'instant' });
          updateHeaderStyle();
        });
      } else {
        if (view !== 'detail') {
          savedGalleryScroll = null;
        }
        scrollViewport.scrollTop = 0;
        window.scrollTo({ top: 0, behavior: 'instant' });
      }

      if (mobShowcaseBar) {
        mobShowcaseBar.style.transform = 'translateX(-50%) translateY(0)';
      }
      updateHeaderStyle();
      if (view === 'detail' && window.innerWidth < 768) {
        updateMobileDockPosition();
      }
    }

    function openPhoto(idx, push = true) {
      captureGalleryScroll();
      currentIdx = idx;
      const p = PHOTOS[idx];
      if (!p) return;
      if (push) {
        const target = '#/photo/' + p.id;
        if (window.location.hash !== target) {
          window.location.hash = target;
          return;
        }
      }
      _applyOpenPhoto(idx);
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
      document.getElementById('hdr-photo-counter').textContent = `${idx + 1} of ${PHOTOS.length}`;
      const mobCounter = document.getElementById('mob-photo-counter');
      if (mobCounter) mobCounter.textContent = `${idx + 1} of ${PHOTOS.length}`;
      document.getElementById('detail-img').src = p.src;

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

    function stepPhoto(dir) {
      const next = (currentIdx + dir + PHOTOS.length) % PHOTOS.length;
      openPhoto(next);
    }

    // Touch Swiping in Fullscreen Lightbox View
    let touchStartX = 0;
    let touchStartY = 0;
    let touchCurrentX = 0;
    let touchStartTime = 0;
    let isTouchSwiping = false;

    const detailStage = document.getElementById('view-detail');
    const detailImg = document.getElementById('detail-img');

    if (detailStage) {
      detailStage.addEventListener('touchstart', (e) => {
        if (currentView !== 'detail' || e.touches.length !== 1) return;
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

    // Keyboard Navigation for Desktop Showcase
    window.addEventListener('keydown', (e) => {
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
        openPhoto(currentIdx);
      } else {
        switchMode('website');
        openPhoto(currentIdx);
      }
    }

    function triggerPrintOrder(btn) {
      const prev = btn.innerHTML;
      btn.innerHTML = "<span>✓ Redirecting to print partner...</span>";
      setTimeout(() => { btn.innerHTML = prev; }, 1400);
    }

    renderGallery();
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
