"""Builds the profile's static, animated SVGs from assets/src.

    pip install pillow fonttools brotli
    python3 scripts/build.py

The live GitHub cards are scripts/github_cards.py's job (run daily by .github/workflows/github-cards.yml).
Everything here is styled on jwardportfolio.vercel.app: its palette, Inter, Nabla headings and mascots."""

import base64
import io
import math
import re

from fontTools.ttLib import TTFont
from PIL import Image

from kit import (ACCENT, ACCENT2, ACCENT_HI, BG, CARD, CARD2, DEEP, FAINT, FG, GLOW, GOLD, GREEN, GREEN_HI, ICONS, LINE,
                 LINE_HI, MUTED, ORANGE, PARTICLE_CSS, SRC, TEXT, data_uri, esc, icon, panel, particles, svg, write)

PORTFOLIO = "https://jwardportfolio.vercel.app"
SUBTLE = "#8a8a8a"  # subtitles on transparent SVGs: readable on GitHub's light and dark themes

_inter = TTFont(SRC / "fonts/inter.woff2")
_cmap = _inter.getBestCmap()
_glyphs = {}


def tw(text, size, weight=400):
    """Width of text set in the embedded Inter, from its own metrics."""
    gs = _glyphs.get(weight) or _glyphs.setdefault(weight, _inter.getGlyphSet(location={"wght": weight}))
    return sum(gs[_cmap.get(ord(c), _cmap[63])].width for c in text) * size / 2048


def wrap(text, size, width, weight=400):
    lines, cur = [], ""
    for word in text.split():
        nxt = f"{cur} {word}".strip()
        if cur and tw(nxt, size, weight) > width:
            lines.append(cur)
            cur = word
        else:
            cur = nxt
    return lines + [cur]


def png(im):
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


_sprites = {}


def mascot(name, pose="idle"):
    key = (name, pose)
    if key not in _sprites:
        _sprites[key] = png(Image.open(SRC / f"mascots/{name}-{pose}.png").resize((192, 192), Image.LANCZOS))
    return _sprites[key]


def pct(t, total):
    return f"{t / total * 100:.3f}%"


def windows(cls, spans, total, fade=0.15):
    """A class whose opacity is 1 inside each (start, end) second span of a looping timeline, 0 outside."""
    on_at_zero = any(a <= 0 for a, _ in spans)
    on_at_end = any(b >= total for _, b in spans)
    pts = [(0, 1 if on_at_zero else 0)]
    for a, b in sorted(spans):
        if a > 0:
            pts += [(a, 0), (min(a + fade, total), 1)]
        if b < total:
            pts += [(b, 1), (min(b + fade, total), 0)]
    pts.append((total, 1 if on_at_end else 0))
    frames = "".join(f"{pct(t, total)}{{opacity:{o}}}" for t, o in pts)
    return f"@keyframes {cls}{{{frames}}}.{cls}{{animation:{cls} {total}s linear infinite}}"


# ─── Hero ────────────────────────────────────────────────────────────────────

J_PATH = "M25 25 L55 25 L55 35 L45 35 L45 75 Q45 90 30 90 Q15 90 15 75 L15 65 L25 65 L25 75 Q25 80 30 80 Q35 80 35 75 L35 25"
W_PATH = "M60 25 L70 25 L75 60 L82.5 25 L92.5 25 L100 60 L105 25 L115 25 L105 95 L95 95 L87.5 55 L80 95 L70 95 L60 25"

MOTION_CSS = (
    "@keyframes rise{0%{opacity:0;transform:translateY(18px)}100%{opacity:1;transform:none}}"
    "@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}"
    "@keyframes fade{from{opacity:0}to{opacity:1}}"
    "@keyframes ping{0%{transform:scale(1);opacity:.75}75%,100%{transform:scale(2.6);opacity:0}}"
    "@keyframes blink{50%{opacity:0}}"
    "@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}"
    "@keyframes ring{0%{transform:scale(.25);opacity:0}30%{opacity:.9}100%{transform:scale(1.35);opacity:0}}"
    "@keyframes spin{to{transform:rotate(360deg)}}"
    ".rise{animation:rise 1s cubic-bezier(.2,.7,.2,1) both}"
    ".float{animation:float 6s ease-in-out infinite}"
    ".fade{animation:fade 1s ease .9s both}"
    ".ping{transform-box:fill-box;transform-origin:center;animation:ping 1.6s cubic-bezier(0,0,.2,1) infinite}"
    ".blink{animation:blink 1.05s steps(1) infinite}"
    ".bob{animation:bob 3.6s ease-in-out infinite}"
    ".ring{transform-box:fill-box;transform-origin:center;animation:ring 3.2s ease-out infinite}"
    ".spin{transform-box:fill-box;transform-origin:center;animation:spin 6s linear infinite}"
)


def split_rows(im):
    """The rendered Nabla block, cut into its lines at the fully transparent rows between them."""
    alpha = im.getchannel("A")
    filled = [alpha.crop((0, y, im.width, y + 1)).getbbox() is not None for y in range(im.height)]
    rows, start = [], None
    for y, f in enumerate(filled + [False]):
        if f and start is None:
            start = y
        elif not f and start is not None:
            if y - start > 8:
                rows.append((start, y))
            start = None
    return rows


def open_pill(x, y, text="Open to Freelance", size=12.5):
    w = tw(text, size, 500) + 46
    return (
        f'<rect x="{x}" y="{y}" width="{w:.1f}" height="30" rx="15" fill="{GREEN}" fill-opacity=".08" stroke="{GREEN}" stroke-opacity=".35"/>'
        f'<circle class="ping" cx="{x + 18}" cy="{y + 15}" r="4" fill="{GREEN}"/>'
        f'<circle cx="{x + 18}" cy="{y + 15}" r="4" fill="{GREEN}"/>'
        f'<text class="s" x="{x + 31}" y="{y + 19.5}" font-size="{size}" font-weight="500" fill="{GREEN_HI}">{esc(text)}</text>'
    ), w


def hero():
    W, H = 1000, 412
    src = Image.open(SRC / "titles/hero.png")
    s, top = 0.34, 50
    lines = ""
    for i, (y0, y1) in enumerate(split_rows(src)):
        crop = src.crop((0, y0, src.width, y1))
        bx0, _, bx1, _ = crop.getbbox()
        crop = crop.crop((bx0, 0, bx1, crop.height))
        w, h = crop.width * s, crop.height * s
        lines += (
            f'<g class="float" style="animation-delay:-{i * 1.4:.1f}s"><g class="rise" style="animation-delay:{0.15 + i * 0.22:.2f}s">'
            f'<image href="{png(crop)}" x="{(W - w) / 2:.1f}" y="{top + y0 * s:.1f}" width="{w:.1f}" height="{h:.1f}"/></g></g>'
        )
    block_bottom = top + src.height * s

    # "Joe Ward | Mobile Engineer", set with the portfolio's sizes and greys
    sy = block_bottom + 40
    parts = [("Joe Ward", FG, 600), ("|", LINE_HI, 300), ("Mobile Engineer", MUTED, 400)]
    gap = 14
    total = sum(tw(t, 22, wt) for t, _, wt in parts) + gap * 2
    x = (W - total) / 2
    sub = ""
    for t, c, wt in parts:
        sub += f'<text class="s" x="{x:.1f}" y="{sy:.1f}" font-size="22" font-weight="{wt}" fill="{c}">{esc(t)}</text>'
        x += tw(t, 22, wt) + gap

    cmd = "$ flutter run --release"
    cw = 13 * 0.6
    cx0 = (W - (len(cmd) + 1.5) * cw) / 2
    cy = sy + 38
    command = (
        f'<text class="m" x="{cx0:.1f}" y="{cy:.1f}" font-size="13"><tspan fill="{FAINT}">$ </tspan>'
        f'<tspan fill="{MUTED}">flutter run --release</tspan></text>'
        f'<rect class="blink" x="{cx0 + (len(cmd) + 0.5) * cw:.1f}" y="{cy - 11:.1f}" width="7.5" height="14" rx="1" fill="{ACCENT}"/>'
    )

    walkers = ""
    for name, mx, my, size, dur in [("asta", 92, 104, 84, 3.4), ("kaneki", 150, 292, 76, 4.1), ("gojo", 838, 96, 84, 3.8),
                                    ("bakugo", 790, 282, 78, 4.5)]:
        walkers += (
            f'<g class="bob" style="animation-duration:{dur}s;animation-delay:-{dur / 3:.1f}s">'
            f'<image href="{mascot(name)}" x="{mx}" y="{my}" width="{size}" height="{size}" opacity=".92"/></g>'
        )

    stars = ""
    for sx, sy0, delay, dur in [(90, 20, 1.5, 11), (380, -10, 6.5, 14)]:
        stars += (
            f'<g transform="translate({sx} {sy0})"><g class="shoot" style="animation-delay:{delay}s;animation-duration:{dur}s">'
            f'<line x1="0" y1="0" x2="-78" y2="-28.5" stroke="url(#tail)" stroke-width="1.6" stroke-linecap="round"/>'
            f'<circle r="1.7" fill="#fff"/></g></g>'
        )
    shoot_css = (
        "@keyframes shoot{0%{transform:translate(0,0);opacity:0}2%{opacity:1}9%{transform:translate(520px,190px);opacity:0}"
        "100%{transform:translate(520px,190px);opacity:0}}.shoot{animation:shoot 11s linear infinite;opacity:0}"
    )
    pill, pill_w = open_pill(W - 24 - (tw("Open to Freelance", 12.5, 500) + 46), 20)
    body = (
        panel(W, H)
        + '<defs><linearGradient id="tail" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="-78" y2="-28.5">'
        '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<radialGradient id="halo" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".16"/>'
        f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient></defs>'
        f'<g clip-path="url(#panel)">{particles(W, H, 58, seed=7)}'
        f'<ellipse cx="{W / 2}" cy="{top + 120}" rx="420" ry="190" fill="url(#halo)"/>{stars}{walkers}</g>'
        f'<g transform="translate(22 14) scale(.3)"><path d="{J_PATH}" fill="{ACCENT}"/><path d="{W_PATH}" fill="{ACCENT}"/></g>'
        f"{pill}{lines}<g class=\"fade\">{sub}{command}</g>"
        f'<text class="m" x="26" y="{H - 22}" font-size="11" fill="{FAINT}">on main · HEAD · still shipping</text>'
    )
    write("hero.svg", svg(W, H, body, PARTICLE_CSS + MOTION_CSS + shoot_css, "Crafting Digital Experiences. Joe Ward, Mobile Engineer"))


# ─── Section titles ──────────────────────────────────────────────────────────

def title(key, label, subtitle, extra=None):
    im = Image.open(SRC / f"titles/{key}.png")
    s = 0.46
    w, h = im.width * s, im.height * s
    W = 1000
    x, y = (W - w) / 2, 4
    uri = data_uri(SRC / f"titles/{key}.png")
    H = y + h + 34
    extra_svg = ""
    if extra:
        pill, pw = open_pill(0, 0, extra, 13)
        extra_svg = f'<g transform="translate({(W - pw) / 2:.1f} {H + 2:.1f})">{pill}</g>'
        H += 46
    body = (
        '<defs><filter id="bright"><feComponentTransfer><feFuncR type="linear" slope="1.8"/>'
        '<feFuncG type="linear" slope="1.8"/><feFuncB type="linear" slope="1.8"/></feComponentTransfer></filter>'
        f'<linearGradient id="sweep" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="150" y2="40">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/>'
        f'<animateTransform attributeName="gradientTransform" type="translate" values="{x - 200:.0f} 0;{x + w + 50:.0f} 0;{x + w + 50:.0f} 0" '
        'keyTimes="0;.32;1" dur="7s" repeatCount="indefinite"/></linearGradient>'
        f'<mask id="shine"><rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h:.1f}" fill="url(#sweep)"/></mask>'
        f'<image id="word" href="{uri}" x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h:.1f}"/></defs>'
        '<g class="float"><use href="#word"/><use href="#word" mask="url(#shine)" filter="url(#bright)" opacity=".55"/></g>'
        f'<text class="s" x="{W / 2}" y="{y + h + 20:.1f}" text-anchor="middle" font-size="15" fill="{SUBTLE}">{esc(subtitle)}</text>'
        f"{extra_svg}"
    )
    write(f"titles/{key}.svg", svg(W, round(H), body, MOTION_CSS, label))


# ─── About ───────────────────────────────────────────────────────────────────

ABOUT = [
    "I'm a Full Stack Flutter Developer with a passion for creating beautiful, functional, and user-centered digital "
    "experiences. With expertise spanning mobile development, web technologies, and AI integration, I bring ideas to "
    "life through code.",
    "My journey started in 2022 when I began my Bachelor's degree, then dove into programming fundamentals in 2023. "
    "By 2024, I found my calling in Flutter development, and since then I've been continuously expanding my skills "
    "from state management to CI/CD pipelines.",
    "Today, I specialize in building production-ready Flutter apps with clean architecture, comprehensive testing, and "
    "smooth animations. I'm always exploring new technologies and pushing my creative boundaries.",
]
CHIPS = ["Flutter Expert", "Clean Architecture", "Full Stack", "Open to Freelance"]


def about():
    W = 1000
    x0, colw, size, lh = 360, 600, 14.5, 23.5
    y = 66
    text = (
        f'<text class="s" x="{x0}" y="{y}" font-size="28" font-weight="600" fill="{FG}">Hi, I\'m '
        f'<tspan fill="{ACCENT}">Joe Ward</tspan></text>'
    )
    y += 40
    for para in ABOUT:
        for line in wrap(para, size, colw):
            text += f'<text class="s" x="{x0}" y="{y:.1f}" font-size="{size}" fill="{TEXT}">{esc(line)}</text>'
            y += lh
        y += 10
    y += 6
    x = x0
    for chip in CHIPS:
        dot = chip == "Open to Freelance"
        cw = tw(chip, 13, 500) + 32 + (14 if dot else 0)
        text += f'<rect x="{x}" y="{y:.1f}" width="{cw:.1f}" height="34" rx="17" fill="{LINE}"/>'
        tx = x + 16
        if dot:
            text += f'<circle class="ping" cx="{x + 18}" cy="{y + 17:.1f}" r="3.5" fill="{GREEN}"/><circle cx="{x + 18}" cy="{y + 17:.1f}" r="3.5" fill="{GREEN}"/>'
            tx += 12
        text += f'<text class="s" x="{tx:.1f}" y="{y + 21.5:.1f}" font-size="13" font-weight="500" fill="{TEXT}">{esc(chip)}</text>'
        x += cw + 10
    H = round(y + 34 + 40)

    fw, fh = 248, 300
    fx, fy = 56, (H - fh) / 2
    me = Image.open(SRC / "me.png")
    avatar = (
        f'<defs><clipPath id="frame"><rect x="{fx}" y="{fy:.1f}" width="{fw}" height="{fh}" rx="16"/></clipPath></defs>'
        f'<g class="float" style="animation-duration:7s">'
        f'<rect x="{fx - 16}" y="{fy - 16:.1f}" width="{fw + 32}" height="{fh + 32}" rx="22" fill="{ACCENT}" fill-opacity=".1"/>'
        f'<rect x="{fx + fw - 80}" y="{fy + fh - 80:.1f}" width="96" height="96" rx="14" fill="{ACCENT}" fill-opacity=".2"/>'
        f'<rect x="{fx}" y="{fy:.1f}" width="{fw}" height="{fh}" rx="16" fill="{CARD2}"/>'
        f'<image href="{png(me)}" x="{fx}" y="{fy:.1f}" width="{fw}" height="{fh}" preserveAspectRatio="xMidYMin slice" clip-path="url(#frame)"/>'
        f'<rect x="{fx + 1}" y="{fy + 1:.1f}" width="{fw - 2}" height="{fh - 2}" rx="15" stroke="{LINE_HI}" stroke-width="2"/></g>'
        f'<g class="float" style="animation-duration:7s"><g class="bob" style="animation-duration:3.2s">'
        f'<image href="{mascot("gojo")}" x="{fx + fw - 58}" y="{fy - 63:.1f}" width="76" height="76"/></g></g>'
    )
    body = panel(W, H, glow=(0.18, 0.5)) + f'<g clip-path="url(#panel)">{particles(W, H, 26, seed=11, alpha=.12)}</g>' + avatar + text
    write("about.svg", svg(W, H, body, PARTICLE_CSS + MOTION_CSS, "About Joe Ward: Full Stack Flutter Developer"))


# ─── Hot reload ──────────────────────────────────────────────────────────────

C_KW, C_TYPE, C_STR, C_NUM, C_PROP, C_PUNCT, C_PLAIN, C_FN, C_COMMENT = (
    ACCENT, ACCENT_HI, "#ffd27a", "#ff9b5a", MUTED, "#737373", "#e5e5e5", ACCENT2, FAINT)
KEYWORDS = {"import", "class", "extends", "const", "return", "super", "false", "true", "void"}
TOKEN = re.compile(r"(//.*$)|('[^']*')|(@\w+)|(0x[0-9A-Fa-f]+)|([A-Za-z_]\w*)(:)?|(\s+)|(.)")


def dart(code):
    out = []
    for m in TOKEN.finditer(code):
        com, st, ann, num, ident, colon, ws, other = m.groups()
        if com:
            out.append((com, C_COMMENT))
        elif st:
            out.append((st, C_STR))
        elif ann:
            out.append((ann, C_KW))
        elif num:
            out.append((num, C_NUM))
        elif ident:
            call = code[m.end():m.end() + 1] == "(" and ident[0].islower()
            color = C_PROP if colon else C_KW if ident in KEYWORDS else C_TYPE if ident[0].isupper() else C_FN if call else C_PLAIN
            out.append((ident, color))
            if colon:
                out.append((":", C_PUNCT))
        elif ws:
            out.append((ws, None))
        else:
            out.append((other, C_PUNCT))
    return out


def code_text(code, x0, y, cw, fs, col=0, cls=""):
    """Each token placed on its own column, so the typing cover and cursor line up whatever font loads."""
    spans = ""
    for tok, color in dart(code):
        if color:
            spans += f'<tspan x="{x0 + col * cw:.2f}" fill="{color}">{esc(tok)}</tspan>'
        col += len(tok)
    klass = f"m {cls}".strip()
    return f'<text class="{klass}" y="{y:.1f}" font-size="{fs}" xml:space="preserve">{spans}</text>'


CODE = [
    "import 'package:flutter/material.dart';",
    "import 'apps.dart';",
    "",
    "void main() => runApp(const Showcase());",
    "",
    "class Showcase extends StatelessWidget {",
    "  const Showcase({super.key});",
    "",
    "  @override",
    "  Widget build(BuildContext context) {",
    "    return MaterialApp(",
    "      debugShowCheckedModeBanner: false,",
    "      theme: AppTheme.dark,",
    "      home: const ZuvoShop(),",
    "    );",
    "  }",
    "}",
]
HOME_LINE = 13
# Real screens from four of my apps, swapped in by retyping `home:` and hot reloading. The last edit brings the
# first app back, so the loop is seamless. (widget, screenshot in assets/src/screens, reload time shown)
APPS = [("ZuvoShop()", "zuvo", "241ms"), ("SurgeXWelcome()", "surgex", "198ms"), ("JukyoStore()", "jukyo", "263ms"),
        ("PlainLivingStats()", "plainliving", "217ms")]
SEGMENT = 5.0  # seconds per app


def timeline():
    """Per edit k (1..4, the 4th retypes the first app): select, type, reload; the phone swaps when it's done."""
    steps = []
    for k in range(1, len(APPS) + 1):
        base = (k - 1) * SEGMENT
        new = APPS[k % len(APPS)][0]
        ts = base + 1.9
        te = ts + len(new) * 0.065
        steps.append(dict(old=APPS[k - 1][0], new=new, sel=base + 1.4, ts=ts, te=te, reload=te + 0.35, done=te + 0.8,
                          app=k % len(APPS), ms=APPS[k % len(APPS)][2]))
    return steps


def hot_reload():
    T = SEGMENT * len(APPS)
    W, H = 1000, 576
    css = [PARTICLE_CSS, MOTION_CSS]
    ex, ey, ew, eh = 24, 42, 560, 492
    fs, lh = 13.5, 20
    cw = fs * 0.6
    gx = ex + 56  # code column 0
    base = ey + 82  # baseline of line 1
    code_bg = "#0c111a"
    steps = timeline()

    lines = ""
    for i, code in enumerate(CODE):
        y = base + i * lh
        lines += f'<text class="m" x="{ex + 40}" y="{y:.1f}" font-size="12" fill="{LINE_HI}" text-anchor="end">{i + 1}</text>'
        if i != HOME_LINE:
            lines += code_text(code, gx, y, cw, fs)

    # the `home:` line: its prefix stays, the widget after it is retyped once per app
    y = base + HOME_LINE * lh
    col = CODE[HOME_LINE].index(APPS[0][0])
    vx = gx + col * cw
    edit = code_text(CODE[HOME_LINE][:col], gx, y, cw, fs)
    edit += code_text(APPS[0][0] + ",", gx, y, cw, fs, col=col, cls="v0")
    css.append(windows("v0", [(0, steps[0]["ts"])], T, fade=0.04))
    for k, s in enumerate(steps):
        n = len(s["new"])
        name = f"h{k}"
        until = steps[k + 1]["ts"] if k + 1 < len(steps) else T
        edit += (
            f'<rect class="{name}sel" x="{vx:.1f}" y="{y - 14:.1f}" width="{len(s["old"]) * cw:.1f}" height="19" rx="2" fill="{ACCENT}" fill-opacity=".32"/>'
            f'<defs><clipPath id="{name}clip"><rect x="{vx:.1f}" y="{y - 16:.1f}" width="{n * cw + 1:.1f}" height="22"/></clipPath></defs>'
            f'<g class="{name}new">{code_text(s["new"], gx, y, cw, fs, col=col)}'
            f'<g clip-path="url(#{name}clip)"><rect class="{name}type" x="{vx:.1f}" y="{y - 16:.1f}" width="{n * cw + 2:.1f}" height="22" fill="{code_bg}"/></g>'
            f'<g class="{name}type">{code_text(",", vx, y, cw, fs)}'
            f'<g class="{name}cur"><rect class="blink" x="{vx - 1:.1f}" y="{y - 13:.1f}" width="2" height="17" fill="{ACCENT_HI}"/></g></g></g>'
        )
        css += [
            windows(f"{name}sel", [(s["sel"], s["ts"])], T, fade=0.05),
            windows(f"{name}new", [(s["ts"], until)], T, fade=0.04),
            windows(f"{name}cur", [(s["ts"], s["te"] + 0.5)], T, fade=0.04),
            f"@keyframes {name}type{{0%,{pct(s['ts'], T)}{{transform:translateX(0);animation-timing-function:steps({n},end)}}"
            f"{pct(s['te'], T)},100%{{transform:translateX({n * cw:.2f}px)}}}}.{name}type{{animation:{name}type {T}s linear infinite}}",
        ]

    # The terminal: each reload's result stays up until the next one starts
    cy1, cy2 = ey + eh - 36, ey + eh - 15
    term = (
        f'<rect x="{ex}" y="{ey + eh - 58}" width="{ew}" height="58" fill="#090c12"/>'
        f'<line x1="{ex}" x2="{ex + ew}" y1="{ey + eh - 58}" y2="{ey + eh - 58}" stroke="{LINE}"/>'
        f'<text class="m" x="{ex + 18}" y="{cy1}" font-size="11.5" fill="{FAINT}">$ flutter run -d "iPhone 16 Pro"</text>'
    )
    for k, s in enumerate(steps):
        nxt = steps[(k + 1) % len(steps)]["reload"]
        shown = [(s["done"], nxt)] if k + 1 < len(steps) else [(s["done"], T), (0, nxt)]
        term += (
            f'<text class="m r{k}" x="{ex + 18}" y="{cy2}" font-size="11.5" fill="{MUTED}">Performing hot reload...</text>'
            f'<text class="m d{k}" x="{ex + 18}" y="{cy2}" font-size="11.5" fill="{GREEN_HI}">Reloaded 1 of 812 libraries in {s["ms"]}.</text>'
        )
        css += [windows(f"r{k}", [(s["reload"], s["done"])], T, fade=0.05), windows(f"d{k}", shown, T, fade=0.05)]

    device = "iPhone 16 Pro · debug"
    editor = (
        f'<defs><clipPath id="ed"><rect x="{ex}" y="{ey}" width="{ew}" height="{eh}" rx="14"/></clipPath></defs>'
        f'<g clip-path="url(#ed)"><rect x="{ex}" y="{ey}" width="{ew}" height="{eh}" fill="{code_bg}"/>'
        f'<rect x="{ex}" y="{ey}" width="{ew}" height="40" fill="#10161f"/>'
        f'<line x1="{ex}" x2="{ex + ew}" y1="{ey + 40}" y2="{ey + 40}" stroke="{LINE}"/>'
        + "".join(f'<circle cx="{ex + 20 + i * 18}" cy="{ey + 20}" r="5.5" fill="{c}"/>' for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]))
        + f'<rect x="{ex + 76}" y="{ey + 6}" width="118" height="34" fill="{code_bg}"/><rect x="{ex + 76}" y="{ey + 6}" width="118" height="2" fill="{ACCENT}"/>'
        f'<image href="{data_uri(SRC / "skills/dart.png")}" x="{ex + 88}" y="{ey + 16}" width="14" height="14"/>'
        f'<text class="m" x="{ex + 108}" y="{ey + 28}" font-size="12" fill="{FG}">main.dart</text>'
        f'<circle cx="{ex + ew - 16 - len(device) * 6.6 - 10:.1f}" cy="{ey + 20}" r="3.5" fill="{GREEN}"/>'
        f'<text class="m" x="{ex + ew - 16}" y="{ey + 24}" font-size="11" fill="{FAINT}" text-anchor="end">{device}</text>'
        f"{lines}{edit}{term}</g>"
        f'<rect x="{ex + .5}" y="{ey + .5}" width="{ew - 1}" height="{eh - 1}" rx="13.5" stroke="{LINE}"/>'
    )

    phone, phone_css = iphone(cx=794, top=(H - 496) / 2, T=T, steps=steps)
    css += phone_css
    body = (
        panel(W, H, glow=(0.8, 0.5))
        + f'<defs><radialGradient id="pglow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".2"/>'
        f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient></defs>'
        f'<g clip-path="url(#panel)">{particles(W, H, 34, seed=21, alpha=.1)}<circle cx="794" cy="{H / 2}" r="260" fill="url(#pglow)"/></g>'
        f"{editor}{phone}"
    )
    label = "Hot reload: retyping one line of Dart swaps the iPhone between real screens of Zuvo, SurgeX, Jukyo Mall and Plain Living"
    write("hot-reload.svg", svg(W, H, body, "".join(css), label))


def iphone(cx, top, T, steps):
    """An iPhone 16 Pro in black titanium, showing whichever of my apps the last hot reload brought up."""
    css = []
    pw, ph, r = 240, 496, 40
    band, bezel = 3.2, 5.6
    px, py = cx - pw / 2, top
    sx, sy = px + band + bezel, py + band + bezel
    sw, sh = pw - 2 * (band + bezel), ph - 2 * (band + bezel)
    sr = r - band - bezel
    defs = (
        '<linearGradient id="ti" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#77777c"/>'
        '<stop offset=".035" stop-color="#3a3a3d"/><stop offset=".5" stop-color="#1f1f21"/><stop offset=".965" stop-color="#3a3a3d"/>'
        '<stop offset="1" stop-color="#77777c"/></linearGradient>'
        '<linearGradient id="tiEdge" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".28"/>'
        '<stop offset=".5" stop-color="#fff" stop-opacity=".06"/><stop offset="1" stop-color="#fff" stop-opacity=".2"/></linearGradient>'
        '<linearGradient id="glare" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".07"/>'
        '<stop offset=".42" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<clipPath id="screen"><rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="{sr}"/></clipPath>'
    )
    buttons = "".join(
        f'<rect x="{x:.1f}" y="{py + y}" width="{w}" height="{h}" rx="1.4" fill="url(#ti)"/>'
        for x, y, w, h in [(px - 2.2, 102, 3.2, 22), (px - 2.2, 144, 3.2, 42), (px - 2.2, 196, 3.2, 42),
                           (px + pw - 1, 168, 3.2, 66), (px + pw - .8, 300, 2.6, 40)]
    )
    shell = (
        f'<ellipse cx="{cx}" cy="{py + ph + 9}" rx="100" ry="8" fill="#000" opacity=".6"/>'
        f"{buttons}"
        f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="{r}" fill="url(#ti)"/>'
        f'<rect x="{px + .6}" y="{py + .6}" width="{pw - 1.2}" height="{ph - 1.2}" rx="{r - .6}" stroke="url(#tiEdge)" stroke-width="1"/>'
        f'<rect x="{px + band}" y="{py + band}" width="{pw - 2 * band}" height="{ph - 2 * band}" rx="{r - band}" fill="#030303"/>'
    )

    # Each reload fades the next app in on top of the current one, which stays opaque underneath until it's covered.
    # The first app is stacked twice: at the bottom for the loop's start, and on top for the last reload back to it.
    ui = f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="#000"/>'
    layers = [(0, [(0, steps[0]["done"] + 0.35)])]
    layers += [(s["app"], [(s["done"], steps[k + 1]["done"] + 0.35)]) for k, s in enumerate(steps[:-1])]
    layers += [(0, [(steps[-1]["done"], T)])]
    for i, (app, spans) in enumerate(layers):
        ui += f'<use class="app{i}" href="#shot{app}"/>'
        css.append(windows(f"app{i}", spans, T, fade=0.2))
    defs += "".join(
        f'<image id="shot{i}" href="{data_uri(SRC / f"screens/{shot}.jpg")}" x="{sx}" y="{sy}" width="{sw}" height="{sh}" preserveAspectRatio="xMidYMid slice"/>'
        for i, (_, shot, _) in enumerate(APPS)
    )

    # the Dynamic Island, which grows into a Live Activity on every reload
    iw, ih = round(sw * 0.33), 21
    island = f'<rect x="{cx - iw / 2}" y="{sy + 6}" width="{iw}" height="{ih}" rx="{ih / 2}" fill="#000"/>'
    for i, s in enumerate(steps):
        a, b = s["done"] + 0.05, s["done"] + 1.5
        aw = sw - 30
        island += (
            f'<g class="isl{i}"><rect x="{cx - aw / 2:.1f}" y="{sy + 5}" width="{aw:.1f}" height="30" rx="15" fill="#000"/>'
            + icon(ICONS["zap"], cx - aw / 2 + 11, sy + 12, 16, GOLD, fill=GOLD)
            + f'<text class="s" x="{cx - aw / 2 + 32:.1f}" y="{sy + 24.5}" font-size="11" font-weight="600" fill="{FG}">Hot reload</text>'
            f'<text class="m" x="{cx + aw / 2 - 13:.1f}" y="{sy + 24.5}" font-size="10.5" fill="{GREEN_HI}" text-anchor="end">{s["ms"]}</text></g>'
        )
        hidden = "opacity:0;transform:scale(.4,.7)"
        css.append(
            f"@keyframes isl{i}{{0%,{pct(a, T)}{{{hidden};animation-timing-function:cubic-bezier(.3,1.4,.5,1)}}"
            f"{pct(a + 0.35, T)},{pct(b - 0.2, T)}{{opacity:1;transform:none}}{pct(b, T)},100%{{{hidden}}}}}"
            f".isl{i}{{transform-box:fill-box;transform-origin:center;animation:isl{i} {T}s linear infinite}}"
        )
    glare = f'<path d="M{sx} {sy}H{sx + sw * 0.6}L{sx} {sy + sh * 0.48}Z" fill="url(#glare)"/>'
    screen = f'<g clip-path="url(#screen)">{ui}{island}{glare}</g>'
    return f"<defs>{defs}</defs>{shell}{screen}", css


# ─── Skills orbit ────────────────────────────────────────────────────────────

SKILL_NAMES = {
    "dart": "Dart", "getx": "GetX", "android": "Android", "apple": "iOS", "flutterflame": "Flame", "hive": "Hive",
    "firebase": "Firebase", "supabase": "Supabase", "fastapi": "FastAPI", "nestjs": "NestJS", "nodejs": "Node.js",
    "postger": "PostgreSQL", "redis": "Redis", "mongodb": "MongoDB", "graphql": "GraphQL", "python": "Python",
    "gemini": "Gemini", "claude": "Claude", "gemma": "Gemma", "react": "React", "next": "Next.js", "ts": "TypeScript",
    "tailwind": "Tailwind", "figma": "Figma", "docker": "Docker", "github": "GitHub", "vercel": "Vercel",
    "google": "Google Cloud",
}
RINGS = [
    (126, 50, 60, ["dart", "getx", "android", "apple", "flutterflame", "hive"], "INNER", "Mobile"),
    (212, 44, -95, ["firebase", "supabase", "fastapi", "nestjs", "nodejs", "postger", "redis", "mongodb", "graphql", "python"], "MIDDLE", "Backend & Data"),
    (298, 40, 140, ["gemini", "claude", "gemma", "react", "next", "ts", "tailwind", "figma", "docker", "github", "vercel", "google"], "OUTER", "AI, Web & Tools"),
]
LIGHT_ON_DARK = {"github"}  # a black glyph: inverted so it reads on the dark tiles


def skill_icon(name):
    im = Image.open(SRC / f"skills/{name}.png").convert("RGBA")
    if name in LIGHT_ON_DARK:
        r, g, b, a = im.split()
        rgb = Image.merge("RGB", (r, g, b)).point(lambda v: 255 - v)
        im = Image.merge("RGBA", (*rgb.split(), a))
    return png(im)


def orbit():
    W, H = 1000, 676
    cx, cy = W / 2, 336
    rings = ""
    for radius, size, period, names, _, _ in RINGS:
        direction = 1 if period > 0 else -1
        dur = abs(period)
        circ = 2 * math.pi * radius
        rings += f'<circle cx="{cx}" cy="{cy}" r="{radius}" stroke="{LINE_HI}" stroke-opacity=".7" stroke-dasharray="2 7"/>'
        comet = "".join(
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" stroke="{ACCENT_HI if i == 2 else ACCENT}" stroke-opacity="{op}" stroke-width="{wd}" '
            f'stroke-linecap="round" stroke-dasharray="{ln} {circ:.1f}" stroke-dashoffset="{-(70 - ln)}"/>'
            for i, (ln, op, wd) in enumerate([(70, .12, 2), (40, .3, 2), (12, .95, 2.6)])
        )
        rings += (
            f'<g>{comet}<animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" '
            f'to="{360 * direction} {cx} {cy}" dur="{dur / 2.2:.1f}s" repeatCount="indefinite"/></g>'
        )
        icons = ""
        for i, name in enumerate(names):
            a = 2 * math.pi * i / len(names) - math.pi / 2 + (0.3 if radius > 200 else 0)
            ix, iy = cx + radius * math.cos(a), cy + radius * math.sin(a)
            h = size / 2
            icons += (
                f'<g transform="translate({ix:.1f} {iy:.1f})"><g>'
                f'<rect x="{-h}" y="{-h}" width="{size}" height="{size}" rx="{size * 0.28:.1f}" fill="{CARD}" stroke="{LINE}"/>'
                f'<image href="{skill_icon(name)}" x="{-h * 0.62:.1f}" y="{-h * 0.62:.1f}" width="{size * 0.62:.1f}" height="{size * 0.62:.1f}"/>'
                f'<text class="s" y="{h + 15}" font-size="10.5" font-weight="500" fill="{MUTED}" text-anchor="middle">{SKILL_NAMES[name]}</text>'
                f'<animateTransform attributeName="transform" type="rotate" from="0" to="{-360 * direction}" dur="{dur}s" repeatCount="indefinite"/>'
                f"</g></g>"
            )
        rings += (
            f'<g>{icons}<animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" '
            f'to="{360 * direction} {cx} {cy}" dur="{dur}s" repeatCount="indefinite"/></g>'
        )

    core = (
        f'<circle cx="{cx}" cy="{cy}" r="92" fill="url(#core)"/>'
        + "".join(f'<circle class="ring" cx="{cx}" cy="{cy}" r="78" stroke="{ACCENT}" stroke-width="1.4" style="animation-delay:{d}s"/>' for d in (0, 1.6))
        + f'<rect x="{cx - 46}" y="{cy - 46}" width="92" height="92" rx="26" fill="{CARD2}" stroke="{ACCENT}" stroke-opacity=".45"/>'
        f'<image href="{skill_icon("flutter")}" x="{cx - 30}" y="{cy - 30}" width="60" height="60"/>'
        f'<text class="s" x="{cx}" y="{cy + 70}" font-size="14" font-weight="700" fill="{FG}" text-anchor="middle">Flutter</text>'
    )
    legend = ""
    for i, (radius, _, _, names, where, what) in enumerate(RINGS):
        ly = H - 74 + i * 22
        legend += (
            f'<circle cx="34" cy="{ly - 4}" r="{4 + i * 1.5}" stroke="{ACCENT}" stroke-opacity="{.4 + i * .2:.1f}" stroke-dasharray="2 2"/>'
            f'<text class="m" x="50" y="{ly}" font-size="11" fill="{FAINT}">{where}<tspan fill="{MUTED}" dx="8">{esc(what)}</tspan></text>'
        )
    total = sum(len(r[3]) for r in RINGS) + 1
    body = (
        panel(W, H, glow=(0.5, 0.5))
        + f'<defs><radialGradient id="core" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".35"/>'
        f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient></defs>'
        f'<g clip-path="url(#panel)">{particles(W, H, 40, seed=31, alpha=.1)}</g>'
        f"{rings}{core}{legend}"
        f'<text class="m" x="{W - 28}" y="38" font-size="11" fill="{FAINT}" text-anchor="end">{total} TOOLS IN ORBIT</text>'
        f'<text class="m" x="28" y="38" font-size="11" fill="{FAINT}">FLUTTER AT THE CORE</text>'
    )
    label = "Skills: Flutter at the core; " + "; ".join(f"{what}: " + ", ".join(SKILL_NAMES[n] for n in names) for _, _, _, names, _, what in RINGS)
    write("skills-orbit.svg", svg(W, H, body, PARTICLE_CSS + MOTION_CSS, label))


# ─── Projects ────────────────────────────────────────────────────────────────

PROJECTS = [
    ("maika", "Maika", "Desktop", "Open source macOS desk companion that watches your Claude Code sessions and levels up from your real work.",
     ["Flutter", "Dart", "Swift", "macOS", "CustomPainter"], 2026, "View source"),
    ("zuvo", "Zuvo", "Mobile", "Social lifestyle platform with AI companion for personalized recommendations and social interactions.",
     ["Flutter", "Dart", "PostgreSQL", "DeepSeek", "FastAPI"], 2025, "See on portfolio"),
    ("plainliving", "Plain Living", "Mobile", "Minimalist lifestyle app focused on simplicity, mindfulness, and intentional living.",
     ["Flutter", "Dart", "Firebase", "GetX"], 2025, "Watch demo"),
    ("wrddgemma", "WRDD Gemma", "Mobile", "AI-powered assistant leveraging Google's Gemma model for intelligent conversations and task automation.",
     ["Flutter", "Dart", "Gemma", "Firebase"], 2026, "Watch demo"),
    ("foundry", "Foundry", "Dev Tool", "Production Flutter starter generator. 21 enterprise-grade modules, one CLI command, zero boilerplate.",
     ["Dart", "Flutter", "Mason", "CLI", "Codegen"], 2026, "See on portfolio"),
    ("jukyomall", "Jukyo Mall", "Mobile", "E-commerce platform with seamless shopping experience and integrated payment solutions.",
     ["Flutter", "Dart", "Dodo Payments", "Firebase", "GetX"], 2025, "Watch demo"),
]


def project_cards():
    W, iw_h = 600, 338
    pad = 26
    desc_lines = {p[0]: wrap(p[3], 15.5, W - 2 * pad) for p in PROJECTS}
    most = max(len(v) for v in desc_lines.values())
    H = round(iw_h + 46 + 30 + most * 24 + 20 + 30 + 34 + 30)
    for k, (key, name, cat, _, tags, year, cta) in enumerate(PROJECTS):
        y = iw_h + 50
        text = f'<text class="s" x="{pad}" y="{y}" font-size="26" font-weight="700" fill="{FG}">{esc(name)}</text>'
        y += 32
        for line in desc_lines[key]:
            text += f'<text class="s" x="{pad}" y="{y}" font-size="15.5" fill="{MUTED}">{esc(line)}</text>'
            y += 24
        y = iw_h + 46 + 30 + most * 24 + 10
        x = pad
        for tag in tags:
            w = tw(tag, 12.5, 500) + 20
            text += (
                f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="28" rx="6" fill="{LINE}"/>'
                f'<text class="s" x="{x + 10:.1f}" y="{y + 18.5}" font-size="12.5" font-weight="500" fill="{MUTED}">{esc(tag)}</text>'
            )
            x += w + 8
        fy = H - 26
        text += (
            f'<line x1="{pad}" x2="{W - pad}" y1="{fy - 30}" y2="{fy - 30}" stroke="{LINE}"/>'
            f'<text class="m" x="{pad}" y="{fy}" font-size="12" fill="{FAINT}">{year} · {cat.lower()}</text>'
            f'<text class="s" x="{W - pad}" y="{fy}" font-size="14" font-weight="600" fill="{ACCENT}" text-anchor="end">{cta}  →</text>'
        )
        cat_w = tw(cat, 12, 500) + 22
        feat_w = tw("Featured", 12, 600) + 22
        chips = (
            f'<rect x="14" y="14" width="{cat_w:.1f}" height="26" rx="13" fill="{BG}" fill-opacity=".72" stroke="#fff" stroke-opacity=".14"/>'
            f'<text class="s" x="25" y="31.5" font-size="12" font-weight="500" fill="{FG}">{cat}</text>'
            f'<rect x="{W - 14 - feat_w:.1f}" y="14" width="{feat_w:.1f}" height="26" rx="13" fill="{ACCENT}"/>'
            f'<text class="s" x="{W - 14 - feat_w + 11:.1f}" y="31.5" font-size="12" font-weight="600" fill="#fff">Featured</text>'
        )
        delay = k * 1.3
        body = (
            f'<defs><clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>'
            f'<linearGradient id="edge" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="{H}">'
            f'<stop offset="0" stop-color="{ACCENT_HI}"/><stop offset=".25" stop-color="{ACCENT}" stop-opacity=".5"/>'
            f'<stop offset=".5" stop-color="{DEEP}" stop-opacity=".1"/><stop offset=".75" stop-color="{ACCENT}" stop-opacity=".5"/>'
            f'<stop offset="1" stop-color="{ACCENT_HI}"/>'
            f'<animateTransform attributeName="gradientTransform" type="rotate" from="0 {W / 2} {H / 2}" to="360 {W / 2} {H / 2}" dur="9s" begin="-{delay}s" repeatCount="indefinite"/></linearGradient>'
            '<linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            '<stop offset=".5" stop-color="#fff" stop-opacity=".16"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            '<linearGradient id="fadeImg" x1="0" y1="0" x2="0" y2="1"><stop offset=".6" stop-color="#000" stop-opacity="0"/>'
            '<stop offset="1" stop-color="#000" stop-opacity=".45"/></linearGradient></defs>'
            f'<g clip-path="url(#card)"><rect width="{W}" height="{H}" fill="{CARD2}"/>'
            f'<image href="{data_uri(SRC / f"projects/{key}.jpg")}" width="{W}" height="{iw_h}" preserveAspectRatio="xMidYMid slice"/>'
            f'<rect width="{W}" height="{iw_h}" fill="url(#fadeImg)"/>'
            f'<g class="sheen" style="animation-delay:{delay}s"><rect x="-260" y="-40" width="200" height="{iw_h + 80}" fill="url(#sheen)" transform="skewX(-18)"/></g>'
            f'<line x1="0" x2="{W}" y1="{iw_h}" y2="{iw_h}" stroke="{LINE}"/>{chips}{text}</g>'
            f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="17.25" stroke="{LINE}" stroke-width="1.5"/>'
            f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="17.25" stroke="url(#edge)" stroke-width="1.5" stroke-opacity=".7"/>'
        )
        sheen_css = "@keyframes sheen{0%{transform:translateX(0)}14%,100%{transform:translateX(1000px)}}.sheen{animation:sheen 8s ease-in-out infinite}"
        write(f"projects/{key}.svg", svg(W, H, body, sheen_css, f"{name}: {PROJECTS[k][3]}"))


# ─── Buttons ─────────────────────────────────────────────────────────────────

BUTTONS = [
    ("portfolio", "globe", "Portfolio", "fill"),
    ("call", "calendar", "Book a call", "outline"),
    ("linkedin", "linkedin", "LinkedIn", "card"),
    ("x", "x", "X", "card"),
    ("instagram", "instagram", "Instagram", "card"),
    ("email", "mail", "Email", "card"),
]


def buttons():
    for key, ic, label, style in BUTTONS:
        h, size = 52, 16
        w = round(22 + 18 + 10 + tw(label, size, 600) + 22)
        bg, stroke, fg, icol = {
            "fill": (ACCENT, ACCENT, "#fff", "#fff"),
            "outline": (BG, ACCENT, ACCENT, ACCENT),
            "card": (CARD2, LINE, FG, MUTED),
        }[style]
        filled = ic == "x"
        body = (
            f'<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="11" fill="{bg}" stroke="{stroke}" stroke-width="1.5"/>'
            + icon(ICONS[ic], 22, (h - 18) / 2, 18, icol, fill=icol if filled else "none")
            + f'<text class="s" x="50" y="{h / 2 + 5.6}" font-size="{size}" font-weight="600" fill="{fg}">{label}</text>'
        )
        write(f"buttons/{key}.svg", svg(w, h, body, "", label))


# ─── Footer ──────────────────────────────────────────────────────────────────

def footer():
    W, H = 1000, 236
    nx, ny = 812, 86
    years = ["2022", "2023", "2024", "2025", "2026"]
    scale = "".join(
        f'<text class="m" x="{600 + i * 88}" y="{H - 34}" font-size="10" fill="{FAINT}" text-anchor="middle">{y}</text>' for i, y in enumerate(years)
    )
    body = (
        panel(W, H, glow=(0.8, 0.35))
        + f'<defs><radialGradient id="node" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".55"/>'
        f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="branch" gradientUnits="userSpaceOnUse" x1="420" y1="{H}" x2="{nx}" y2="{ny}">'
        f'<stop offset="0" stop-color="{ACCENT}" stop-opacity="0"/><stop offset="1" stop-color="{ACCENT_HI}"/></linearGradient></defs>'
        f'<g clip-path="url(#panel)">{particles(W, H, 26, seed=41, alpha=.12)}'
        f'<line x1="420" y1="{H + 20}" x2="{nx}" y2="{ny}" stroke="url(#branch)" stroke-width="2.4"/>'
        f'<line class="flow" x1="420" y1="{H + 20}" x2="{nx}" y2="{ny}" stroke="{ACCENT_HI}" stroke-width="2.4" stroke-dasharray="6 60" stroke-linecap="round" stroke-opacity=".9"/>'
        f'<circle cx="{nx}" cy="{ny}" r="90" fill="url(#node)" class="float"/>'
        f'<circle cx="{nx}" cy="{ny}" r="11" fill="#e8f0fc"/><circle class="ring" cx="{nx}" cy="{ny}" r="26" stroke="{ACCENT_HI}" stroke-width="1.4"/>'
        f'<text class="m" x="{nx + 20}" y="{ny + 4}" font-size="10.5" fill="{MUTED}">HEAD → main</text>'
        f'<g class="bob" style="animation-duration:3.4s"><image href="{mascot("gabimaru")}" x="{nx + 46}" y="{ny + 14}" width="76" height="76"/></g>'
        f"</g>"
        f'<g transform="translate(66 94)"><g class="spin"><circle r="13" stroke="{ACCENT}" stroke-width="2" stroke-dasharray="4 5"/></g><circle r="4" fill="{ACCENT}"/></g>'
        f'<text class="s" x="96" y="132" font-size="112" font-weight="900" fill="none" stroke="{ACCENT}" stroke-opacity=".6" stroke-width="1.3" letter-spacing="-2">HEAD</text>'
        f'<text class="s" x="48" y="150" font-size="38" font-weight="800" fill="{FG}" letter-spacing="-.5">Still shipping</text>'
        f'<text class="s" x="50" y="178" font-size="15" fill="{MUTED}">The next release is in progress.</text>'
        f'<text class="m" x="50" y="{H - 30}" font-size="12.5"><tspan fill="{FAINT}">$ </tspan><tspan fill="{MUTED}">git push origin main</tspan></text>'
        f'<rect class="blink" x="{50 + 22.5 * 7.5:.1f}" y="{H - 41}" width="7" height="13" rx="1" fill="{ACCENT}"/>'
        f"{scale}"
        f'<line x1="600" x2="952" y1="{H - 24}" y2="{H - 24}" stroke="{LINE}" stroke-width="2"/>'
        f'<line class="grow" x1="600" x2="952" y1="{H - 24}" y2="{H - 24}" stroke="{ACCENT}" stroke-width="2"/>'
    )
    css = (
        PARTICLE_CSS + MOTION_CSS
        + "@keyframes flow{to{stroke-dashoffset:-66}}.flow{animation:flow 1.6s linear infinite}"
        + "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}.grow{transform-box:fill-box;transform-origin:left;animation:grow 2.4s cubic-bezier(.2,.7,.2,1) .4s both}"
    )
    write("footer.svg", svg(W, H, body, css, "HEAD: still shipping. The next release is in progress."))


if __name__ == "__main__":
    hero()
    title("about", "About Me", "A passionate developer on a mission to create impactful digital experiences")
    title("hotreload", "Hot Reload", "One line of Dart, one hot reload, another app I've shipped")
    title("skills", "My Skills", "A diverse toolkit spanning mobile development, web technologies, and AI integration")
    title("projects", "My Projects", "A collection of projects that showcase my skills and passion for building exceptional digital experiences")
    title("github", "GitHub Activity", "Live from my GitHub, refreshed every day")
    title("contact", "Get In Touch", "Have a project in mind or want to collaborate? I'd love to hear from you.", extra="Open to Freelance Projects")
    about()
    hot_reload()
    orbit()
    project_cards()
    buttons()
    footer()
