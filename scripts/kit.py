"""Shared bits for the profile's SVGs: the portfolio's palette, embedded fonts and small helpers. Stdlib only,
so the GitHub Action can import it without installing anything."""

import base64
import math
import pathlib
import random
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "src"
OUT = ROOT / "assets"

# jwardportfolio.vercel.app, globals.css and the --jr-* tokens
BG = "#0a0a0a"
CARD = "#141414"
CARD2 = "#1a1a1a"
LINE = "#262626"
LINE_HI = "#404040"
FG = "#fafafa"
TEXT = "#d4d4d4"
MUTED = "#a3a3a3"
FAINT = "#525252"
ACCENT = "#5994eb"
ACCENT2 = "#7aabf0"
ACCENT_HI = "#b6d1ff"
DEEP = "#1b3f86"
NAVY = "#04101f"
GLOW = "#0d1628"
GOLD = "#ffd214"
ORANGE = "#ff9123"
GREEN = "#22c55e"
GREEN_HI = "#4ade80"

MASCOTS = ["kaneki", "jinwoo", "asta", "gojo", "kirito", "bakugo", "gabimaru"]


def data_uri(path, mime=None):
    path = pathlib.Path(path)
    mime = mime or {".png": "image/png", ".jpg": "image/jpeg", ".woff2": "font/woff2"}[path.suffix]
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def font_css(body):
    """Embeds only the faces the body uses (class "s" is Inter, class "m" is Geist Mono)."""
    css = ""
    if re.search(r'class="(?:[^"]* )?s[ "]', body):
        css += (
            f"@font-face{{font-family:'Inter';font-weight:100 900;src:url({data_uri(SRC / 'fonts/inter.woff2')}) format('woff2')}}"
            ".s{font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif}"
        )
    if re.search(r'class="(?:[^"]* )?m[ "]', body):
        css += (
            f"@font-face{{font-family:'Geist Mono';font-weight:100 900;src:url({data_uri(SRC / 'fonts/geistmono.woff2')}) format('woff2')}}"
            ".m{font-family:'Geist Mono',ui-monospace,SFMono-Regular,Menlo,monospace}"
        )
    return css


def svg(w, h, body, css="", label=""):
    reduce = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}" fill="none">'
        f"<title>{esc(label)}</title><style>{font_css(body)}{css}{reduce}</style>{body}</svg>"
    )


def write(name, text):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"  {name:34} {len(text) // 1024:>5} KB")


def panel(w, h, r=20, glow=(0.72, 0.45)):
    """The portfolio's backdrop: near-black with the radial navy glow, a 1px #262626 edge."""
    gx, gy = glow
    return (
        f'<defs><radialGradient id="bgGlow" cx="{gx}" cy="{gy}" r="0.75">'
        f'<stop offset="0" stop-color="{GLOW}"/><stop offset="0.62" stop-color="{BG}"/></radialGradient>'
        f'<clipPath id="panel"><rect width="{w}" height="{h}" rx="{r}"/></clipPath></defs>'
        f'<rect width="{w}" height="{h}" rx="{r}" fill="url(#bgGlow)"/>'
        f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="{r - 0.5}" stroke="{LINE}"/>'
    )


PARTICLE_CSS = (
    "@keyframes tw{0%,100%{opacity:.25}50%{opacity:1}}.tw{animation:tw 5s ease-in-out infinite}"
    "@keyframes drift{0%,100%{transform:translate(0,0)}50%{transform:translate(-12px,7px)}}"
    ".drift{animation:drift 28s ease-in-out infinite}"
)


def particles(w, h, n, seed, reach=125, alpha=0.2):
    """The portfolio's constellation: blue particles joined by faint white lines, twinkling and drifting."""
    rng = random.Random(seed)
    pts = [(rng.uniform(-20, w + 20), rng.uniform(-20, h + 20)) for _ in range(n)]
    lines, dots = [], []
    for i, (x1, y1) in enumerate(pts):
        near = sorted((math.dist((x1, y1), p), j) for j, p in enumerate(pts) if j > i)
        for d, j in near[:3]:
            if d < reach:
                x2, y2 = pts[j]
                lines.append(
                    f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#fff" '
                    f'stroke-opacity="{(1 - d / reach) * alpha:.3f}" stroke-width="0.6"/>'
                )
        dots.append(
            f'<circle class="tw" cx="{x1:.1f}" cy="{y1:.1f}" r="{rng.uniform(0.8, 2.1):.2f}" fill="{ACCENT}" '
            f'style="animation-delay:-{rng.uniform(0, 6):.2f}s;animation-duration:{rng.uniform(3.5, 7.5):.2f}s"/>'
        )
    return f'<g class="drift">{"".join(lines)}{"".join(dots)}</g>'


def icon(paths, x, y, size, color, width=2, fill="none"):
    """A 24x24 Lucide (stroke) or Simple Icons (fill) glyph placed at x,y."""
    s = size / 24
    stroke = f'stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"' if fill == "none" else ""
    return f'<g transform="translate({x:.1f} {y:.1f}) scale({s:.4f})" fill="{fill}" {stroke}>{paths}</g>'


ICONS = {
    "github": '<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/>',
    "star": '<path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "repo": '<path d="M9 20H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H20a2 2 0 0 1 2 2v5"/><circle cx="13" cy="12" r="2"/><path d="M18 19c-2.8 0-5-2.2-5-5v8"/><circle cx="20" cy="19" r="2"/>',
    "commit": '<circle cx="12" cy="12" r="3"/><line x1="3" x2="9" y1="12" y2="12"/><line x1="15" x2="21" y1="12" y2="12"/>',
    "zap": '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "linkedin": '<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect width="4" height="12" x="2" y="9"/><circle cx="4" cy="4" r="2"/>',
    "instagram": '<rect width="20" height="20" x="2" y="2" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" x2="17.51" y1="6.5" y2="6.5"/>',
    "mail": '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    "calendar": '<path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/>',
    "house": '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "grid": '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "chevron": '<path d="m9 18 6-6-6-6"/>',
    "rocket": '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
    "x": '<path d="M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.154h7.594l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z"/>',
    "googleplay": '<path d="M22.018 13.298l-3.919 2.218-3.515-3.493 3.543-3.521 3.891 2.202a1.49 1.49 0 0 1 0 2.594zM1.337.924a1.486 1.486 0 0 0-.112.568v21.017c0 .217.045.419.124.6l11.155-11.087L1.337.924zm12.207 10.065l3.258-3.238L3.45.195a1.466 1.466 0 0 0-.946-.179l11.04 10.973zm0 2.067l-11 10.933c.298.036.612-.016.906-.183l13.324-7.54-3.23-3.21z"/>',
    "appstore": '<path d="M8.8086 14.9194l6.1107-11.0368c.0837-.1513.1682-.302.2437-.4584.0685-.142.1267-.2854.1646-.4403.0803-.3259.0588-.6656-.066-.9767-.1238-.3095-.3417-.5678-.6201-.7355a1.4175 1.4175 0 0 0-.921-.1924c-.3207.043-.6135.1935-.8443.4288-.1094.1118-.1996.2361-.2832.369-.092.1463-.175.2979-.259.4492l-.3864.6979-.3865-.6979c-.0837-.1515-.1667-.303-.2587-.4492-.0837-.1329-.1739-.2572-.2835-.369-.2305-.2353-.5233-.3857-.844-.429a1.4181 1.4181 0 0 0-.921.1926c-.2784.1677-.4964.426-.6203.7355-.1246.311-.1461.6508-.066.9767.038.155.0962.2984.1648.4403.0753.1564.1598.307.2437.4584l1.248 2.2543-4.8625 8.7825H2.0295c-.1676 0-.3351-.0007-.5026.0092-.1522.009-.3004.0284-.448.0714-.3108.0906-.5822.2798-.7783.548-.195.2665-.3006.5929-.3006.9279 0 .3352.1057.6612.3006.9277.196.2683.4675.4575.7782.548.1477.043.296.0623.4481.0715.1675.01.335.009.5026.009h13.0974c.0171-.0357.059-.1294.1-.2697.415-1.4151-.6156-2.843-2.0347-2.843zM3.113 18.5418l-.7922 1.5008c-.0818.1553-.1644.31-.2384.4705-.067.1458-.124.293-.1611.452-.0785.3346-.0576.6834.0645 1.0029.1212.3175.3346.583.607.7549.2727.172.5891.2416.9013.1975.3139-.044.6005-.1986.8263-.4402.1072-.1148.1954-.2424.2772-.3787.0902-.1503.1714-.3059.2535-.4612L6 19.4636c-.0896-.149-.9473-1.4704-2.887-.9218m20.5861-3.0056a1.4707 1.4707 0 0 0-.779-.5407c-.1476-.0425-.2961-.0616-.4483-.0705-.1678-.0099-.3352-.0091-.503-.0091H18.648l-4.3891-7.817c-.6655.7005-.9632 1.485-1.0773 2.1976-.1655 1.0333.0367 2.0934.546 3.0004l5.2741 9.3933c.084.1494.167.299.2591.4435.0837.131.1739.2537.2836.364.231.2323.5238.3809.8449.4232.3192.0424.643-.0244.9217-.1899.2784-.1653.4968-.4204.621-.7257.1246-.3072.146-.6425.0658-.9641-.0381-.1529-.0962-.2945-.165-.4346-.0753-.1543-.1598-.303-.2438-.4524l-1.216-2.1662h1.596c.1677 0 .3351.0009.5029-.009.1522-.009.3007-.028.4483-.0705a1.4707 1.4707 0 0 0 .779-.5407A1.5386 1.5386 0 0 0 24 16.452a1.539 1.539 0 0 0-.3009-.9158Z"/>',
}
