"""Build the LinkedIn banner in the jamesphillipsanders.com type and palette.

LinkedIn wants 1584 x 396. Its profile photo covers roughly the bottom left
quarter of that on desktop and mobile, so nothing important goes there. The
banner deliberately carries no rate, because the LinkedIn profile is also open
to permanent roles.

Writes SVGs next to the header ones; render them to PNG in a browser.
    python tools/build_banner.py
"""

import math

from build_header import PALETTES, ROOT, advance, contrast, load_font, oklch_to_hex, spans, woff2_b64

W, H = 1584, 396
LEFT, RIGHT = 448, 96  # left edge clears the profile photo; right margin

KICKER = "DATA ENGINEER · PONTE DE LIMA, PORTUGAL · EU HOURS"
LINE1 = [("The pipeline ran green.", "ink")]
LINE2 = [("The numbers are ", "ink"), ("still wrong", "accent"), (".", "ink")]
STACK = "Python · dbt · Redshift · AWS"
URL = "jamesphillipsanders.com"


def build():
    display, mono = load_font("display"), load_font("mono")
    track = -0.025
    width = W - LEFT - RIGHT
    widest = max(advance(display, "".join(t for t, _ in line), 1, track) for line in (LINE1, LINE2))
    head = math.floor(width / widest)
    mono_size, kick_size = 25, 20
    assert advance(mono, STACK, mono_size) + advance(mono, URL, mono_size) + 80 < width, "bottom row overflows"
    assert advance(mono, KICKER, kick_size, 0.14) < width, "kicker overflows"

    text_display = "".join(t for t, _ in LINE1 + LINE2)
    text_mono = KICKER + STACK + URL
    fonts_css = (
        f"@font-face{{font-family:D;src:url(data:font/woff2;base64,{woff2_b64(display, text_display)}) format('woff2')}}"
        f"@font-face{{font-family:M;src:url(data:font/woff2;base64,{woff2_b64(mono, text_mono)}) format('woff2')}}"
    )

    kicker_y = 92
    line1_y = kicker_y + 28 + round(head * 0.72)
    line2_y = line1_y + round(head * 1.08)
    rule_y = line2_y + 40
    row_y = rule_y + 46

    for name, tokens in PALETTES.items():
        c = {k: oklch_to_hex(v) for k, v in tokens.items()}
        for role in ("ink", "soft", "accent"):
            assert contrast(c[role], c["bg"]) >= 4.5, f"{name} {role} under AA"
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<style>{fonts_css}.d{{font-family:D,ui-sans-serif,system-ui,sans-serif;font-weight:500;letter-spacing:{track}em}}.m{{font-family:M,ui-monospace,SFMono-Regular,Menlo,monospace}}</style>
<rect width="{W}" height="{H}" fill="{c['bg']}"/>
<text class="m" x="{LEFT}" y="{kicker_y}" font-size="{kick_size}" letter-spacing="0.14em" fill="{c['soft']}">{KICKER}</text>
<text class="d" x="{LEFT - 3}" y="{line1_y}" font-size="{head}">{spans(LINE1, c)}</text>
<text class="d" x="{LEFT - 3}" y="{line2_y}" font-size="{head}">{spans(LINE2, c)}</text>
<line x1="{LEFT}" y1="{rule_y}" x2="{W - RIGHT}" y2="{rule_y}" stroke="{c['rule']}" stroke-width="2"/>
<text class="m" x="{LEFT}" y="{row_y}" font-size="{mono_size}" fill="{c['ink']}">{STACK}</text>
<text class="m" x="{W - RIGHT}" y="{row_y}" font-size="{mono_size}" text-anchor="end" fill="{c['accent']}">{URL}</text>
</svg>
"""
        out = ROOT / "assets" / f"linkedin-banner-{name}.svg"
        out.write_text(svg)
        print(f"wrote {out.relative_to(ROOT)}  headline {head}px  rows at {kicker_y}, {line1_y}, {line2_y}, {rule_y}, {row_y}")


if __name__ == "__main__":
    build()
