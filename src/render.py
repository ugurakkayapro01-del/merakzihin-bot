"""Merak Zihin — carousel görsellerini (1080x1350 JPEG) üretir."""
import html
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FONTS = os.path.join(ROOT, "fonts")
GOLD = "#D4A93C"

# Özgün, sade çizgi ikonlar (viewBox 0 0 100 100)
ICONS = {
    "beyin": '<path d="M50 22c-6-8-20-7-23 3-9 1-14 10-10 18-6 5-5 15 2 19 0 9 9 15 17 12 4 6 11 6 14 0M50 22c6-8 20-7 23 3 9 1 14 10 10 18 6 5 5 15-2 19 0 9-9 15-17 12-4 6-11 6-14 0M50 22v54M36 38c5 3 9 3 14 0M50 52c5 3 11 3 16-1M33 56c5 2 11 1 17-4"/>',
    "psikoloji": '<path d="M38 82V70c-9-5-14-13-14-24 0-16 12-27 28-27 15 0 25 11 25 24 0 4 0 6 2 10l4 6c1 2 0 3-2 3h-3v6c0 4-3 6-7 6h-6v8"/><circle cx="52" cy="42" r="8"/><path d="M52 30v4M52 50v4M40 42h4M60 42h4"/>',
    "uyku": '<path d="M62 20a32 32 0 1 0 18 50A26 26 0 0 1 62 20z"/><path d="M70 26h10l-10 12h10M78 44h7l-7 8h7"/>',
    "duygu": '<path d="M50 80S20 62 20 40c0-10 8-18 17-18 6 0 10 3 13 8 3-5 7-8 13-8 9 0 17 8 17 18 0 22-30 40-30 40z"/><path d="M34 44h8l4-8 6 16 4-8h10"/>',
    "davranis": '<path d="M12 50s14-24 38-24 38 24 38 24-14 24-38 24S12 50 12 50z"/><circle cx="50" cy="50" r="11"/><circle cx="54" cy="46" r="3" fill="GOLDC" stroke="none"/>',
    "bilim": '<circle cx="50" cy="50" r="5" fill="GOLDC" stroke="none"/><ellipse cx="50" cy="50" rx="36" ry="13"/><ellipse cx="50" cy="50" rx="36" ry="13" transform="rotate(60 50 50)"/><ellipse cx="50" cy="50" rx="36" ry="13" transform="rotate(120 50 50)"/>',
    "uzay": '<circle cx="50" cy="50" r="18"/><ellipse cx="50" cy="50" rx="36" ry="10" transform="rotate(-20 50 50)"/><circle cx="18" cy="20" r="1.5" fill="GOLDC"/><circle cx="84" cy="24" r="2" fill="GOLDC"/><circle cx="80" cy="80" r="1.5" fill="GOLDC"/>',
    "tarih": '<path d="M30 16h40M30 84h40M34 16c0 18 32 22 32 34S34 66 34 84M66 16c0 18-32 22-32 34s32 16 32 34"/><path d="M44 76h12"/>',
    "vucut": '<path d="M10 52h18l7-16 10 32 9-26 6 10h30"/>',
    "fikir": '<path d="M50 16c-14 0-24 10-24 23 0 9 5 14 9 19 3 3 4 6 4 10h22c0-4 1-7 4-10 4-5 9-10 9-19 0-13-10-23-24-23z"/><path d="M40 76h20M42 84h16M50 38v14M44 44l6 8 6-8"/>',
}


def marks(text):
    """[[vurgu]] → altın renkli span; geri kalanı HTML-güvenli."""
    parts = re.split(r"(\[\[.*?\]\])", text)
    out = []
    for p in parts:
        if p.startswith("[[") and p.endswith("]]"):
            out.append(f'<span class="g">{html.escape(p[2:-2])}</span>')
        else:
            out.append(html.escape(p))
    return "".join(out)


def css():
    f = lambda n: "file://" + os.path.join(FONTS, n)
    return f"""
@font-face{{font-family:Anton;src:url({f('anton-latin-400-normal.woff2')})}}
@font-face{{font-family:Anton;src:url({f('anton-latin-ext-400-normal.woff2')});unicode-range:U+0100-024F}}
@font-face{{font-family:Inter;font-weight:700;src:url({f('inter-latin-700-normal.woff2')})}}
@font-face{{font-family:Inter;font-weight:700;src:url({f('inter-latin-ext-700-normal.woff2')});unicode-range:U+0100-024F}}
@font-face{{font-family:Inter;font-weight:800;src:url({f('inter-latin-800-normal.woff2')})}}
@font-face{{font-family:Inter;font-weight:800;src:url({f('inter-latin-ext-800-normal.woff2')});unicode-range:U+0100-024F}}
*{{box-sizing:border-box}}
html,body{{margin:0;width:1080px;height:1350px;background:#0D0D0D;overflow:hidden}}
.g{{color:{GOLD}}}
.page{{position:relative;width:1080px;height:1350px;background:#0D0D0D}}
.art{{position:absolute;left:0;right:0;top:0;height:760px;background:radial-gradient(ellipse at 50% 48%,#2a2a2a 0%,#141414 55%,#0D0D0D 80%)}}
.art svg{{position:absolute;left:50%;top:120px;transform:translateX(-50%);width:460px;height:460px}}
.band{{position:absolute;left:0;right:0;top:700px;bottom:0;display:flex;flex-direction:column;align-items:center;padding:0 70px}}
.logo{{font:400 44px Anton;color:#fff;letter-spacing:2px;margin-bottom:24px}}
.h{{font-family:Anton;color:#fff;text-align:center;text-transform:uppercase;line-height:1.15;max-height:400px}}
.sub{{font:700 34px/1.35 Inter;color:#cfcfcf;text-align:center;margin-top:24px}}
.swipe{{position:absolute;bottom:50px;left:0;right:0;text-align:center;font:800 26px Inter;color:#fff;letter-spacing:4px}}
.handle{{position:absolute;bottom:52px;right:60px;font:700 24px Inter;color:#777}}
.num{{position:absolute;top:60px;right:70px;font:700 26px Inter;color:#666}}
.inner{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 90px}}
.st{{font:400 50px Anton;color:{GOLD};margin-bottom:40px;text-transform:uppercase}}
.sb{{font-family:Inter;font-weight:700;color:#fff;line-height:1.45}}
.mz{{position:absolute;bottom:58px;left:90px;font:400 40px Anton;color:#fff}}
.cta{{text-align:center}}
.cta .big{{font:400 88px/1.1 Anton;color:#fff;text-transform:uppercase}}
.cta .small{{font:700 36px/1.5 Inter;color:#cfcfcf;margin-top:36px}}
"""


def page(body):
    return f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><style>{css()}</style></head><body>{body}</body></html>'


def cover(item):
    icon = ICONS.get(item["category"], ICONS["fikir"]).replace("GOLDC", GOLD)
    return page(f"""<div class="page"><div class="art"><svg viewBox="0 0 100 100" fill="none" stroke="{GOLD}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">{icon}</svg></div>
<div class="band"><div class="logo">M<span class="g">Z</span></div><div class="h" id="fit">{marks(item['headline'])}</div>
<div class="sub">{marks(item['subline'])}</div></div><div class="swipe">KAYDIR →</div><div class="handle">@merakzihin</div></div>""")


def slide(s, i, n):
    return page(f"""<div class="page"><div class="num">{i}/{n}</div><div class="inner"><div class="st">{html.escape(s['title'])}</div>
<div class="sb" id="fit">{marks(s['body'])}</div></div><div class="mz">M<span class="g">Z</span></div><div class="handle" style="bottom:64px">@merakzihin</div></div>""")


def cta(i, n):
    return page(f"""<div class="page"><div class="num">{i}/{n}</div><div class="inner cta">
<div style="font:400 120px Anton;color:#fff;margin-bottom:40px">M<span class="g">Z</span></div>
<div class="big">Merak eden <span class="g">zihin</span> büyür</div>
<div class="small">Her gün yeni bir “Bunu bilmiyordum!”<br>Kaydet, arkadaşına gönder, <span class="g">@merakzihin</span>'i takip et.</div>
</div></div>""")


# Metni kutusuna sığana kadar küçült (taşma olmaz)
FIT_JS = """([start, min, maxH]) => {
  const el = document.getElementById('fit'); if (!el) return 0;
  let s = start; el.style.fontSize = s + 'px';
  while ((el.scrollHeight > maxH || el.scrollWidth > el.clientWidth + 2) && s > min) { s -= 2; el.style.fontSize = s + 'px'; }
  return s;
}"""


def render(item, outdir):
    os.makedirs(outdir, exist_ok=True)
    slides = item["slides"]
    total = len(slides) + 2
    pages = [(cover(item), (104, 60, 390))]
    for i, s in enumerate(slides, start=2):
        pages.append((slide(s, i, total), (56, 38, 820)))
    pages.append((cta(total, total), None))
    files = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for idx, (doc, fit) in enumerate(pages, start=1):
            tmp = os.path.join(outdir, f"_p{idx}.html")
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(doc)
            pg.goto("file://" + os.path.abspath(tmp), wait_until="load")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(250)
            if fit:
                pg.evaluate(FIT_JS, list(fit))
            path = os.path.join(outdir, f"{idx:02d}.jpg")
            pg.screenshot(path=path, type="jpeg", quality=92)
            files.append(path)
            os.remove(tmp)
        b.close()
    return files


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        item = json.load(f)
    for f in render(item, sys.argv[2]):
        print(f)
