"""Draws the live GitHub cards: assets/github-activity.svg and assets/contributions.svg.

The numbers come from the portfolio's own /api/github (the same ones its GitHub Activity section shows), the
languages from GitHub's GraphQL API with GITHUB_TOKEN. Stdlib only; .github/workflows/github-cards.yml runs it
daily. If the portfolio can't be reached, the last good cards are kept."""

import datetime
import json
import math
import os
import sys
import urllib.request

from kit import (ACCENT, ACCENT_HI, CARD, DEEP, FAINT, FG, ICONS, LINE, MASCOTS, MUTED, PARTICLE_CSS, SRC, data_uri,
                 esc, icon, panel, particles, svg, write)

USER = "joewrdd"
STATS_URL = "https://jwardportfolio.vercel.app/api/github"
LEVELS = ["#1a1a1a", "#1a3c73", "#3369b5", ACCENT, ACCENT_HI]
LANG_COLORS = [ACCENT, "#7aabf0", ACCENT_HI, "#3369b5", DEEP, "#404040"]
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def fetch(url, body=None, token=None):
    headers = {"User-Agent": f"{USER}-profile-cards", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def languages(token):
    if not token:
        return []
    query = """query($login:String!){user(login:$login){repositories(first:100,ownerAffiliations:OWNER,isFork:false,
      privacy:PUBLIC){nodes{languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}}}"""
    try:
        repos = fetch("https://api.github.com/graphql", {"query": query, "variables": {"login": USER}}, token)["data"]["user"]["repositories"]["nodes"]
    except Exception as e:  # languages are a nice-to-have; the card draws without them
        print(f"::warning::languages unavailable: {e}")
        return []
    totals = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            totals[edge["node"]["name"]] = totals.get(edge["node"]["name"], 0) + edge["size"]
    total = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda kv: -kv[1])
    out = [(name, size / total) for name, size in top[:5]]
    rest = sum(size for _, size in top[5:]) / total
    return out + ([("Other", rest)] if rest > 0.005 else [])


def odometer(value, x, baseline, size, uid):
    """The number rolls in like a split-flap counter: every digit spins a full turn and lands on its value."""
    col, line = size * 0.66, size * 1.12
    out, css, i = "", "", 0
    for ch in f"{value:,}":
        if not ch.isdigit():
            out += f'<text class="s" x="{x:.1f}" y="{baseline}" font-size="{size}" font-weight="800" fill="{FG}">{ch}</text>'
            x += size * 0.3
            continue
        stack = "".join(
            f'<text class="s" x="{x + col / 2:.1f}" y="{baseline + k * line:.1f}" font-size="{size}" font-weight="800" fill="{FG}" text-anchor="middle">{k % 10}</text>'
            for k in range(20)
        )
        out += (
            f'<defs><clipPath id="{uid}{i}"><rect x="{x - 2:.1f}" y="{baseline - size:.1f}" width="{col + 4:.1f}" height="{size * 1.2:.1f}"/></clipPath></defs>'
            f'<g clip-path="url(#{uid}{i})"><g class="{uid}{i}">{stack}</g></g>'
        )
        css += (
            f"@keyframes {uid}{i}{{from{{transform:translateY(0)}}to{{transform:translateY(-{(10 + int(ch)) * line:.1f}px)}}}}"
            f".{uid}{i}{{animation:{uid}{i} {1.4 + i * 0.25:.2f}s cubic-bezier(.15,.75,.2,1) {0.2 + i * 0.08:.2f}s both}}"
        )
        x += col
        i += 1
    return out, css


def activity(stats, langs):
    W = 1000
    H = 300 if langs else 222
    tile_w, tile_h, gap, top = (W - 48 - 3 * 16) / 4, 172, 16, 24
    weekly = [sum(d["count"] for d in w) for w in (stats.get("weeks") or [])]
    tiles = [
        ("repo", "REPOSITORIES", stats["repos"], "public, built by me"),
        ("commit", "CONTRIBUTIONS", stats.get("contributions") or 0, "in the last 12 months"),
        ("star", "STARS", stats["totalStars"], "across my repositories"),
        ("users", "FOLLOWERS", stats["followers"], "on GitHub"),
    ]
    body, css = panel(W, H, glow=(0.5, 0.2)), [PARTICLE_CSS]
    body += f'<g clip-path="url(#panel)">{particles(W, H, 30, seed=51, alpha=.1)}</g>'
    for i, (ic, label, value, caption) in enumerate(tiles):
        x = 24 + i * (tile_w + gap)
        body += (
            f'<rect x="{x:.1f}" y="{top}" width="{tile_w:.1f}" height="{tile_h}" rx="14" fill="{CARD}" stroke="{LINE}"/>'
            + icon(ICONS[ic], x + 18, top + 17, 13, FAINT)
            + f'<text class="m" x="{x + 38:.1f}" y="{top + 28}" font-size="10.5" fill="{FAINT}" letter-spacing="1.4">{label}</text>'
        )
        num, num_css = odometer(value, x + 18, top + 98, 54, f"n{i}")
        body += num
        css.append(num_css)
        vy = top + 128
        if ic == "repo":
            n = min(value, 34)
            body += "".join(
                f'<rect class="pop" x="{x + 18 + k * 5.6:.1f}" y="{vy}" width="3" height="12" rx="1" fill="{ACCENT}" style="animation-delay:{0.6 + k * 0.03:.2f}s"/>'
                for k in range(n)
            )
        elif ic == "commit" and weekly:
            peak = max(weekly) or 1
            w = tile_w - 36
            pts = [(x + 18 + k * w / (len(weekly) - 1), vy + 16 - 18 * v / peak) for k, v in enumerate(weekly)]
            line = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
            body += (
                f'<polygon points="{line} {pts[-1][0]:.1f},{vy + 17} {pts[0][0]:.1f},{vy + 17}" fill="{ACCENT}" fill-opacity=".14"/>'
                f'<polyline class="draw" points="{line}" stroke="{ACCENT}" stroke-width="1.6" stroke-linejoin="round" pathLength="100" stroke-dasharray="100"/>'
            )
        elif ic == "star":
            body += "".join(
                f'<g class="pop" style="animation-delay:{0.6 + k * 0.12:.2f}s">' + icon(ICONS["star"], x + 18 + k * 18, vy - 1, 13, ACCENT, fill=ACCENT) + "</g>"
                for k in range(min(value, 11))
            )
        else:
            n = max(min(value, 24), 1)
            cx, cy, r = x + 30, vy + 4, 11
            dots = "".join(
                f'<circle cx="{cx + r * math.cos(2 * math.pi * k / n):.1f}" cy="{cy + r * math.sin(2 * math.pi * k / n):.1f}" r="1.6" fill="{ACCENT}"/>'
                for k in range(n)
            )
            body += f'<g class="spin">{dots}</g><circle cx="{cx}" cy="{cy}" r="3" fill="{ACCENT_HI}"/>'
        body += f'<text class="m" x="{x + 18:.1f}" y="{top + tile_h - 14}" font-size="10" fill="{FAINT}">{caption}</text>'

    if langs:
        y = top + tile_h + 32
        body += f'<text class="m" x="24" y="{y}" font-size="10.5" fill="{FAINT}" letter-spacing="1.4">TOP LANGUAGES</text>'
        bx, bw = 24, W - 48
        body += f'<defs><clipPath id="bar"><rect x="{bx}" y="{y + 12}" width="{bw}" height="10" rx="5"/></clipPath></defs><g clip-path="url(#bar)"><g class="grow">'
        lx = bx
        for k, (name, share) in enumerate(langs):
            body += f'<rect x="{lx:.1f}" y="{y + 12}" width="{bw * share + 1:.1f}" height="10" fill="{LANG_COLORS[k % len(LANG_COLORS)]}"/>'
            lx += bw * share
        body += "</g></g>"
        lx = bx
        for k, (name, share) in enumerate(langs):
            text = f"{name} {share * 100:.1f}%"
            body += (
                f'<circle cx="{lx + 5}" cy="{y + 42}" r="4.5" fill="{LANG_COLORS[k % len(LANG_COLORS)]}"/>'
                f'<text class="s" x="{lx + 15}" y="{y + 46.5}" font-size="12.5" fill="{MUTED}">{esc(name)} <tspan fill="{FAINT}">{share * 100:.1f}%</tspan></text>'
            )
            lx += len(text) * 7.2 + 34
    css.append(
        "@keyframes pop{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}"
        ".pop{animation:pop .5s ease both}"
        "@keyframes draw{from{stroke-dashoffset:100}to{stroke-dashoffset:0}}.draw{animation:draw 2.2s ease-out .5s both}"
        "@keyframes spin{to{transform:rotate(360deg)}}.spin{transform-box:fill-box;transform-origin:center;animation:spin 14s linear infinite}"
        "@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}.grow{transform-box:fill-box;transform-origin:left;animation:grow 1.8s cubic-bezier(.2,.7,.2,1) .4s both}"
    )
    label = f"GitHub: {stats['repos']} repositories, {stats.get('contributions')} contributions in the last year, {stats['totalStars']} stars, {stats['followers']} followers"
    write("github-activity.svg", svg(W, H, body, "".join(css), label))


def contributions(stats, today):
    weeks = stats.get("weeks")
    if not weeks:
        return
    W, H = 1000, 262
    pitch, cell = 16, 12
    gx = (W - (len(weeks) * pitch - 4)) / 2
    gy = 76
    floor = gy + 7 * pitch + 38
    T = 26.0
    x_start, x_end = gx - 34, gx + len(weeks) * pitch + 30
    walker = MASCOTS[today.toordinal() % len(MASCOTS)]

    body, css = panel(W, H, glow=(0.5, 0.0)), [PARTICLE_CSS]
    body += (
        f'<g clip-path="url(#panel)">{particles(W, H, 22, seed=61, alpha=.08)}</g>'
        + icon(ICONS["github"], 26, 24, 17, FG)
        + f'<text class="s" x="52" y="38" font-size="15" font-weight="600" fill="{FG}">Contribution Activity</text>'
        f'<text class="s" x="{W - 26}" y="38" font-size="13" fill="{MUTED}" text-anchor="end">{stats.get("contributions") or 0:,} in the last year</text>'
    )
    for row, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        body += f'<text class="m" x="{gx - 10:.1f}" y="{gy + row * pitch + 9.5}" font-size="9.5" fill="{FAINT}" text-anchor="end">{name}</text>'
    last_month = None
    cells, glows = "", ""
    for c, week in enumerate(weeks):
        x = gx + c * pitch
        month = int(week[0]["date"][5:7])
        if month != last_month and c < len(weeks) - 2:
            body += f'<text class="m" x="{x:.1f}" y="{gy - 10}" font-size="10" fill="{FAINT}">{MONTHS[month - 1]}</text>'
            last_month = month
        col, glow = "", ""
        for day in week:
            r = datetime.date.fromisoformat(day["date"]).weekday()
            row = (r + 1) % 7  # GitHub's grid starts on Sunday
            y = gy + row * pitch
            col += f'<rect x="{x:.1f}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{LEVELS[day["level"]]}"/>'
            glow += f'<rect x="{x:.1f}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="#e8f0fc" fill-opacity="{0.9 if day["level"] else 0.16}"/>'
        cells += f'<g class="cin" style="animation-delay:{c * 0.012:.3f}s">{col}</g>'
        glows += f'<g class="g{c}">{glow}</g>'
        # the walker crosses this column twice a loop: going right, then coming back
        cx = x + cell / 2
        t1 = (cx - x_start) / (x_end - x_start) * T / 2
        t2 = T / 2 + (x_end - cx) / (x_end - x_start) * T / 2
        frames = ["0%{opacity:0}"]
        for t in (t1, t2):
            frames += [f"{max(t - 0.15, 0) / T * 100:.2f}%{{opacity:0}}", f"{t / T * 100:.2f}%{{opacity:1}}", f"{min(t + 1.1, T) / T * 100:.2f}%{{opacity:0}}"]
        frames.append("100%{opacity:0}")
        css.append(f"@keyframes g{c}{{{''.join(frames)}}}.g{c}{{animation:g{c} {T}s linear infinite;opacity:0}}")
    body += cells + glows
    size = 62
    body += (
        f'<line x1="{gx - 20:.1f}" x2="{gx + len(weeks) * pitch + 16:.1f}" y1="{floor}" y2="{floor}" stroke="{LINE}" stroke-dasharray="3 5"/>'
        f'<g class="walk"><g class="turn">'
        f'<image class="fa" href="{data_uri(SRC / f"mascots/{walker}-walkA.png")}" x="{-size / 2}" y="{floor - size * 0.8:.1f}" width="{size}" height="{size}"/>'
        f'<image class="fb" href="{data_uri(SRC / f"mascots/{walker}-walkB.png")}" x="{-size / 2}" y="{floor - size * 0.8:.1f}" width="{size}" height="{size}"/>'
        f"</g></g>"
    )
    legend_x = W - 26 - 5 * 16 - 34
    body += (
        f'<text class="m" x="26" y="{H - 20}" font-size="10.5" fill="{FAINT}">today\'s walker: <tspan fill="{MUTED}">{walker}</tspan></text>'
        f'<text class="m" x="{legend_x - 8}" y="{H - 20}" font-size="10" fill="{FAINT}" text-anchor="end">Less</text>'
        + "".join(f'<rect x="{legend_x + k * 16}" y="{H - 30}" width="12" height="12" rx="2.5" fill="{LEVELS[k]}"/>' for k in range(5))
        + f'<text class="m" x="{legend_x + 5 * 16 + 4}" y="{H - 20}" font-size="10" fill="{FAINT}">More</text>'
    )
    css.append(
        "@keyframes cin{from{opacity:0}to{opacity:1}}.cin{animation:cin .6s ease both}"
        f"@keyframes walk{{0%{{transform:translateX({x_start:.1f}px)}}50%{{transform:translateX({x_end:.1f}px)}}100%{{transform:translateX({x_start:.1f}px)}}}}"
        f".walk{{animation:walk {T}s linear infinite}}"
        "@keyframes turn{0%,49.99%{transform:scaleX(1)}50%,100%{transform:scaleX(-1)}}"
        f".turn{{transform-box:fill-box;transform-origin:center;animation:turn {T}s linear infinite}}"
        "@keyframes step{0%,49.99%{opacity:1}50%,100%{opacity:0}}.fa{animation:step .38s linear infinite}"
        ".fb{animation:step .38s linear -.19s infinite}"
    )
    label = f"{stats.get('contributions')} contributions in the last year, walked by {walker}"
    write("contributions.svg", svg(W, H, body, "".join(css), label))


def main():
    try:
        stats = fetch(STATS_URL)
        stats["repos"], stats["followers"], stats["totalStars"]
    except Exception as e:
        print(f"::warning::portfolio stats unavailable, keeping the last cards: {e}")
        return 0
    activity(stats, languages(os.environ.get("GITHUB_TOKEN")))
    contributions(stats, datetime.date.today())
    return 0


if __name__ == "__main__":
    sys.exit(main())
