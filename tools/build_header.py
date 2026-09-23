"""Build the profile header SVGs in the jamesphillipsanders.com type and palette.

Fonts are pinned from the Google Fonts variable files, cut down to the glyphs the
header uses, and embedded as woff2, because an SVG shown through an <img> tag
cannot fetch web fonts. Every text colour is checked against WCAG AA before
anything is written.

Run with a Python that has fonttools and brotli:
    python tools/build_header.py
"""

import base64
import io
import math
import pathlib
import urllib.request

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.subset import Options, Subsetter

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / "tools" / ".fonts"
FONTS = {
    "display": ("https://github.com/google/fonts/raw/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf", 500),
    "mono": ("https://github.com/google/fonts/raw/main/ofl/jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf", 400),
}

KICKER = "CONTRACT DATA ENGINEER · PONTE DE LIMA, PORTUGAL · EU HOURS"
LINE1 = [("The pipeline ran green.", "ink")]
LINE2 = [("The numbers are ", "ink"), ("still wrong", "accent"), (".", "ink")]
STRIP = [
    ("EUR 400", "accent"), (" per day", "ink"), ("   ", "ink"),
    ("Available", "accent"), (" now", "ink"), ("   ", "ink"),
    ("Remote", "accent"), (", EU hours", "ink"), ("   ", "ink"),
    ("Python", "accent"), (" · dbt · Redshift · AWS", "ink"),
]

# The site's tokens, in oklch, plus a dark set derived from the same hues.
PALETTES = {
    "light": {"bg": (0.973, 0.008, 78), "ink": (0.205, 0.014, 62), "soft": (0.505, 0.020, 66),
              "rule": (0.878, 0.012, 74), "accent": (0.545, 0.128, 52)},
    "dark": {"bg": (0.205, 0.014, 62), "ink": (0.955, 0.008, 78), "soft": (0.740, 0.018, 70),
             "rule": (0.330, 0.014, 62), "accent": (0.740, 0.125, 58)},
}

W, H, PAD = 1600, 620, 96


def oklch_to_hex(lch):
    L, C, h = lch
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (
        4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )

    def enc(x):
        x = min(max(x, 0.0), 1.0)
        return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055

    return "#" + "".join(f"{round(enc(c) * 255):02x}" for c in rgb)


def luminance(hex_):
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg, bg):
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def load_font(key):
    url, weight = FONTS[key]
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{key}.ttf"
    if not path.exists():
        urllib.request.urlretrieve(url, path)
    font = TTFont(path)
    return instancer.instantiateVariableFont(font, {"wght": weight})


def advance(font, text, size, tracking=0.0):
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    upm = font["head"].unitsPerEm
    return sum(hmtx[cmap[ord(ch)]][0] for ch in text) * size / upm + tracking * size * max(len(text) - 1, 0)


def woff2_b64(font, text):
    opts = Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    sub = Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def spans(parts, colors):
    return "".join(f'<tspan fill="{colors[c]}">{t.replace("&", "&amp;")}</tspan>' for t, c in parts)


def build():
    display, mono = load_font("display"), load_font("mono")
    text_display = "".join(t for t, _ in LINE1 + LINE2)
    text_mono = KICKER + "".join(t for t, _ in STRIP)

    track = -0.025
    widest = max(advance(display, "".join(t for t, _ in line), 1, track) for line in (LINE1, LINE2))
    head_size = math.floor((W - 2 * PAD) / widest)
    strip_size = 27
    assert advance(mono, "".join(t for t, _ in STRIP), strip_size) < W - 2 * PAD, "strip overflows"
    assert advance(mono, KICKER, 21, 0.14) < W - 2 * PAD, "kicker overflows"

    fonts_css = (
        f"@font-face{{font-family:D;src:url(data:font/woff2;base64,{woff2_b64(display, text_display)}) format('woff2')}}"
        f"@font-face{{font-family:M;src:url(data:font/woff2;base64,{woff2_b64(mono, text_mono)}) format('woff2')}}"
    )

    for name, tokens in PALETTES.items():
        c = {k: oklch_to_hex(v) for k, v in tokens.items()}
        for role in ("ink", "soft", "accent"):
            ratio = contrast(c[role], c["bg"])
            assert ratio >= 4.5, f"{name} {role} contrast {ratio:.2f} is under 4.5"
            print(f"{name:5s} {role:6s} {c[role]} on {c['bg']}  {ratio:.2f}:1")

        y1, y2 = 262, 262 + round(head_size * 1.08)
        rule1, strip_y, rule2 = y2 + 70, y2 + 138, y2 + 188
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t">
<title id="t">James Phillip Sanders, contract data engineer. The pipeline ran green. The numbers are still wrong.</title>
<style>{fonts_css}.d{{font-family:D,ui-sans-serif,system-ui,sans-serif;font-weight:500;letter-spacing:{track}em}}.m{{font-family:M,ui-monospace,SFMono-Regular,Menlo,monospace}}</style>
<rect width="{W}" height="{H}" fill="{c['bg']}"/>
<text class="m" x="{PAD}" y="118" font-size="21" letter-spacing="0.14em" fill="{c['soft']}">{KICKER}</text>
<text class="d" x="{PAD - 4}" y="{y1}" font-size="{head_size}">{spans(LINE1, c)}</text>
<text class="d" x="{PAD - 4}" y="{y2}" font-size="{head_size}">{spans(LINE2, c)}</text>
<line x1="{PAD}" y1="{rule1}" x2="{W - PAD}" y2="{rule1}" stroke="{c['rule']}" stroke-width="2"/>
<text class="m" x="{PAD}" y="{strip_y}" font-size="{strip_size}" xml:space="preserve">{spans(STRIP, c)}</text>
<line x1="{PAD}" y1="{rule2}" x2="{W - PAD}" y2="{rule2}" stroke="{c['rule']}" stroke-width="2"/>
</svg>
"""
        out = ROOT / "assets" / f"header-{name}.svg"
        out.write_text(svg)
        print(f"wrote {out.relative_to(ROOT)}  {len(svg) // 1024} KB  headline {head_size}px")


if __name__ == "__main__":
    build()
