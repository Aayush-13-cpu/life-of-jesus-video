"""Build the book PDF: docs/book/book.md + appendices generated from the code -> HTML -> PDF (headless Chrome).

  .venv/bin/python docs/book/build_book.py        (needs: pip install markdown; google-chrome on PATH)

The reference appendices (verbs, props, templates, the video library) are read from the code and the library files,
so the book always matches the version of the machine it was built from.
"""
import datetime, html, json, os, re, subprocess, sys
import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "longform"))
sys.path.insert(0, os.path.join(ROOT, "shorts"))
import lineart, build_long  # noqa: E402
import kit, build_short     # noqa: E402

TITLE = "The Life of Jesus Video Machine"
SUB = "A complete guide, from your first terminal command to building your own automated video channel"
OUT = os.path.join(HERE, "The-Life-of-Jesus-Video-Machine.pdf")


def stamp(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def verbs(template):
    return sorted(set(re.findall(r"^\s{6}(\w+): a =>", template, re.M)))


def appendices():
    e = html.escape
    out = []

    # B: the vocabulary of a scene
    lv, sv = verbs(build_long.TEMPLATE), verbs(build_short.TEMPLATE)
    out.append("## Appendix B — Scene Vocabulary\n\nGenerated from the code of this version.\n")
    out.append("### Long videos (`longform/`)\n")
    out.append("| What | Allowed values |\n|---|---|")
    out.append(f"| skies (`sky`) | {' '.join(f'`{s}`' for s in lineart.SKIES)} |")
    out.append(f"| lands (`land`) | {' '.join(f'`{s}`' for s in lineart.LANDS)} |")
    out.append(f"| people (`k`) | {' '.join(f'`{s}`' for s in sorted(lineart.PEOPLE))} |")
    out.append(f"| props (`k`) | {' '.join(f'`{s}`' for s in sorted(lineart.PROPS))} |")
    out.append("| groups (`k`) | `crowd` (with `n`, the number of people) |")
    out.append(f"| effects (`fx`) | {' '.join(f'`{s}`' for s in sorted(lineart.FX))} |")
    out.append(f"| verbs (`do`) | {' '.join(f'`{s}`' for s in lv)} |\n")
    out.append("### Shorts (`shorts/`)\n")
    out.append("| What | Allowed values |\n|---|---|")
    out.append(f"| skies (`sky`) | {' '.join(f'`{s}`' for s in kit.SKIES)} |")
    out.append("| grounds (`ground`) | `hills` `field` `desert` `city` `sea` `garden` |")
    out.append(f"| people (`k`) | {' '.join(f'`{s}`' for s in sorted(kit.PEOPLE))} |")
    out.append(f"| props (`k`) | {' '.join(f'`{s}`' for s in sorted(kit.PROPS))} |")
    out.append("| effects (`fx`) | `lightning` `rain` `rays` `sparkle` |")
    out.append(f"| verbs (`do`) | {' '.join(f'`{s}`' for s in sv)} |\n")
    out.append("""### What the main verbs do

| Verb | Needs | Effect |
|---|---|---|
| `walk`, `run` | `to` (x) | move across the ground, with a bob |
| `climb` | `to` (y) | move up or down (a mat lowered through a roof, an ascension) |
| `fly` | `to` (x), `toy` (y) | move freely through the air (birds) |
| `roll` | `to` (x), optional `deg` | move and spin (a stone rolled away) |
| `raise`, `bless`, `reach`, `lower` | — | arm gestures: both arms up, right arm up, right arm forward, arms down |
| `kneel`, `stand`, `lie` | — | bend the body: kneel, stand back up, lie flat |
| `appear`, `vanish` | — | fade in, fade out |
| `rock`, `drift` | optional `amp`, `period` | tilt or slide back and forth (boats, waves) |
| `grow` | — | grow from nothing (a tree, a plant) |
| `flicker` | — | a flame flickers (lamps, fires) |
| `sink`, `collapse`, `tint` | Shorts only | sink, fall away, change a jar's colour |

Every act may have `at` (seconds into the beat, default 0) and `dur` (seconds; default: until the beat ends).
""")

    # C: the templates
    out.append('<div class="page-break"></div>\n\n## Appendix C — The Twenty Templates\n')
    out.append("Each long video uses one template: a line colour, a glow, five sky gradients and a moving motif. "
               "A template in use is marked with its video.\n")
    used = {v["template"]: v["title"] for v in build_long.videos()}
    rows = ['<table class="swatches"><tr><th>Template</th><th>Line</th><th>Glow</th><th>Night</th><th>Dawn</th>'
            '<th>Dusk</th><th>Day</th><th>Storm</th><th>Motif</th><th>Used by</th></tr>']
    for name, t in lineart.TEMPLATES.items():
        sw = lambda c: f'<td><span class="chip" style="background:{c}"></span></td>'
        sky = lambda s: (f'<td><span class="chip" style="background:linear-gradient({t["skies"][s][0]},'
                         f'{t["skies"][s][1]})"></span></td>')
        rows.append(f'<tr><td><code>{name}</code></td>{sw(t["line"])}{sw(t["glow"])}'
                    + "".join(sky(s) for s in lineart.SKIES)
                    + f'<td>{t["motif"]}</td><td>{e(used.get(name, "free"))}</td></tr>')
    out.append("\n".join(rows) + "</table>\n")

    # D: the library
    out.append('<div class="page-break"></div>\n\n## Appendix D — The Library\n')
    out.append("### Long videos, in upload order\n")
    out.append("Lengths are the self-check's estimate (at the measured 3.24 words per second).\n")
    for i, v in enumerate(build_long.videos(), 1):
        t = sum(build_long.estimate(c) for c in v["chapters"])
        beats = sum(len(c["beats"]) for c in v["chapters"])
        chs = " · ".join(e(c["title"]) for c in v["chapters"])
        out.append(f"**{i}. {e(v['title'])}** — `{v['id']}`, template `{v['template']}`, "
                   f"{len(v['chapters'])} chapters, {beats} beats, about {stamp(t)}  \n<span class=\"small\">{chs}</span>\n")
    lib = json.load(open(os.path.join(ROOT, "shorts", "stories_library.json"), encoding="utf-8"))
    out.append("### The Shorts library (`shorts/stories_library.json`), in order\n")
    out.append("| # | Title | Scripture | Style |\n|---|---|---|---|")
    for i, s in enumerate(lib, 1):
        out.append(f"| {i} | {e(s['title'])} | {e(s['ref'])} | {s.get('style', 'silhouette')} |")
    out.append("")
    return "\n".join(out)


CSS = """
@font-face { font-family: "Cinzel"; src: url("../../fonts/Cinzel.ttf"); }
@font-face { font-family: "Cormorant"; src: url("../../fonts/CormorantGaramond.ttf"); }
@font-face { font-family: "Cormorant"; font-style: italic; src: url("../../fonts/CormorantGaramond-Italic.ttf"); }
@page { size: A4; margin: 22mm 20mm 24mm 20mm;
        @bottom-center { content: counter(page); font: 9pt "Source Serif 4", Georgia, serif; color: #8a7a60; } }
@page :first { @bottom-center { content: none; } }
:root { --ink: #1d1a16; --gold: #9a7428; --soft: #f6f1e6; --line: #e3d8c2; }
html { font: 11pt/1.55 "Source Serif 4", Georgia, "DejaVu Serif", serif; color: var(--ink); }
body { margin: 0; }
h1, h2, h3 { font-family: "Cormorant", Georgia, serif; color: #2a2116; line-height: 1.15; break-after: avoid; }
h1 { font-size: 30pt; font-weight: 600; margin: 0 0 14pt; padding-bottom: 6pt; border-bottom: 1.5pt solid var(--gold); }
h2 { font-size: 19pt; font-weight: 600; margin: 22pt 0 8pt; }
h3 { font-size: 14pt; font-weight: 600; margin: 16pt 0 6pt; }
p, li { orphans: 3; widows: 3; }
a { color: inherit; text-decoration: none; }
code { font: 9pt "JetBrains Mono", "DejaVu Sans Mono", monospace; font-variant-ligatures: none; background: var(--soft); padding: 0 2pt; border-radius: 2pt; }
pre { background: #1f1b16; color: #f3e9d6; padding: 9pt 11pt; border-radius: 5pt; overflow: hidden;
      font-size: 7.8pt; line-height: 1.45;
      white-space: pre-wrap; word-break: break-word; break-inside: avoid; }
pre code { background: none; color: inherit; padding: 0; font-size: 7.8pt; line-height: 1.45; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0 12pt; font-size: 9.5pt; break-inside: auto; }
th, td { border-bottom: 0.6pt solid var(--line); padding: 4pt 6pt; text-align: left; vertical-align: top; }
th { background: var(--soft); font-weight: 600; }
tr { break-inside: avoid; }
blockquote { margin: 10pt 0; padding: 8pt 12pt; background: var(--soft); border-left: 3pt solid var(--gold);
             break-inside: avoid; }
blockquote p { margin: 0; }
img { display: block; max-width: 100%; margin: 10pt auto 4pt; border-radius: 4pt; break-inside: avoid; }
p:has(> img) { text-align: center; font-size: 9pt; color: #6b5d48; break-inside: avoid; }
.page-break { break-after: page; }
.small { font-size: 9pt; color: #5d5140; }
.chip { display: inline-block; width: 22pt; height: 14pt; border-radius: 3pt; border: 0.5pt solid #bbb; }
table.swatches td, table.swatches th { padding: 3pt 4pt; font-size: 8.5pt; }
.try { background: #eef5ea; border-left: 3pt solid #5f8f4a; padding: 8pt 12pt; margin: 10pt 0; break-inside: avoid; }
.cover { height: 250mm; display: flex; flex-direction: column; justify-content: center; text-align: center;
         break-after: page; }
.cover .t { font: 34pt "Cinzel", serif; letter-spacing: 2pt; color: #2a2116; }
.cover .s { font: italic 16pt "Cormorant", serif; color: #6b5d48; margin: 14pt 30mm 0; }
.cover .r { width: 60mm; height: 1pt; background: var(--gold); margin: 22pt auto; }
.cover .m { font-size: 10pt; color: #8a7a60; }
.toc { break-after: page; }
.toc h1 { border: none; }
.toc ol { list-style: none; padding: 0; margin: 0; }
.toc li.l1 { font: 600 13pt "Cormorant", serif; margin-top: 9pt; }
.toc li.l2 { margin-left: 16pt; font-size: 10pt; }
"""


def toc(tokens):
    items = []

    def walk(ts):
        for t in ts:
            if t["level"] <= 2:
                items.append(f'<li class="l{t["level"]}"><a href="#{t["id"]}">{t["name"]}</a></li>')
            walk(t["children"])
    walk(tokens)
    return f'<div class="toc"><h1>Contents</h1><ol>{"".join(items)}</ol></div>'


def main():
    src = open(os.path.join(HERE, "book.md"), encoding="utf-8").read()
    assert src.count("<!-- GENERATED -->") == 1, "book.md needs one <!-- GENERATED --> marker for the appendices"
    src = src.replace("<!-- GENERATED -->", appendices())
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "md_in_html", "attr_list"])
    body = md.convert(src)
    today = datetime.date.today().strftime("%B %Y")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{TITLE}</title>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=JetBrains+Mono:wght@400&display=block" rel="stylesheet">
<style>{CSS}</style></head><body>
<div class="cover"><div class="t">{TITLE}</div><div class="r"></div><div class="s">{SUB}</div>
<div class="r"></div><div class="m">Built from the repository on {today}</div></div>
{toc(md.toc_tokens)}
{body}
</body></html>"""
    path = os.path.join(HERE, "book.html")
    open(path, "w", encoding="utf-8").write(page)
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--generate-pdf-document-outline", "--virtual-time-budget=20000",
                    f"--print-to-pdf={OUT}", "file://" + path], check=True, capture_output=True)
    print(f"{OUT} ({os.path.getsize(OUT) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
