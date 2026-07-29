#!/usr/bin/env python3
"""Render a founder-facing design-evidence page from a small JSON manifest.

The whole point of this script is that the model NEVER authors page markup.
It writes a manifest (a few hundred tokens); this file emits the HTML.

Usage:
    python3 build_evidence.py <manifest.json> [-o <out.html>] [--inline]

    --inline   embed PNGs as data URIs (single portable file, bigger)
    default    reference images by relative path (small file, keep the folder)

Manifest shape (only `pr`/`title` and `surfaces` are required):

{
  "pr": 1367,
  "title": "Add /learn to the main nav",
  "url": "https://github.com/gaia-research/gaia-skill-tree/pull/1367",
  "summary": "One line on what changed and why.",
  "gaps": [
    "No dark theme captured: neither prefers-color-scheme nor data-theme
     appears in docs/ for these pages, so there is exactly one theme."
  ],
  "surfaces": [
    {
      "name": "Homepage nav",
      "route": "/",
      "note": "New Learn item sits between Explore and Named.",
      "shots": [
        {"viewport": "desktop 1280x800", "before": "img/home-nav-desktop-before.png",
                                         "after":  "img/home-nav-desktop-after.png"},
        {"viewport": "mobile 375x812",   "after":  "img/home-nav-mobile-after.png",
                                         "added": true}
      ]
    }
  ]
}

A shot with `added: true` (or simply no `before`) renders as a single frame
labelled "added - no before". Exit codes: 0 ok, 2 bad manifest.
"""

import argparse
import base64
import html
import json
import mimetypes
import sys
from datetime import date
from pathlib import Path

CSS = """
*,*::before,*::after{box-sizing:border-box}
body{margin:0;background:#0f1115;color:#e6e8ee;
 font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 -webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:32px 20px 72px}
header{border-bottom:1px solid #262a33;padding-bottom:20px;margin-bottom:28px}
.eyebrow{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:#7f8899;margin:0 0 8px}
h1{font-size:23px;line-height:1.3;margin:0 0 10px;font-weight:650}
h1 .num{color:#7f8899;font-weight:450}
.summary{margin:0;color:#aab2c0;max-width:78ch}
.meta{margin:14px 0 0;font-size:13px;color:#7f8899}
.meta a{color:#8fb4ff}
.gaps{border:1px solid #4a3a12;background:#1d1708;border-radius:8px;
 padding:14px 16px;margin:24px 0 0}
.gaps h2{font-size:13px;letter-spacing:.05em;text-transform:uppercase;
 color:#e3b341;margin:0 0 8px;font-weight:600}
.gaps ul{margin:0;padding-left:18px;color:#d8cfae}
.gaps li+li{margin-top:6px}
section.surface{margin-top:40px}
section.surface>h2{font-size:17px;margin:0 0 4px;font-weight:600}
.route{font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:#7f8899}
.note{margin:8px 0 0;color:#aab2c0;max-width:78ch}
.shot{margin-top:22px}
.vp{font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:#7f8899;
 margin:0 0 8px;text-transform:none}
.pair{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.pair.single{grid-template-columns:minmax(0,1fr);max-width:760px}
figure{margin:0;min-width:0;border:1px solid #262a33;border-radius:8px;
 background:#151821;overflow:hidden}
figcaption{font-size:12px;letter-spacing:.06em;text-transform:uppercase;
 color:#7f8899;padding:9px 12px;border-bottom:1px solid #262a33;background:#12151d}
figcaption.after{color:#7ee0a8}
figcaption.added{color:#8fb4ff}
figure .frame{overflow-x:auto}
img{display:block;width:100%;height:auto;max-width:100%}
.missing{padding:26px 14px;color:#c0616a;font-size:13px;text-align:center}
footer{margin-top:56px;border-top:1px solid #262a33;padding-top:16px;
 font-size:12.5px;color:#6b7383}
@media (max-width:640px){.wrap{padding:22px 14px 56px}h1{font-size:20px}}
"""


def esc(value):
    return html.escape(str(value), quote=True)


def dataUri(path):
    kind = mimetypes.guess_type(path.name)[0] or "image/png"
    return "data:%s;base64,%s" % (kind, base64.b64encode(path.read_bytes()).decode())


def imgTag(src, base, inline, alt):
    if not src:
        return '<div class="missing">no image path in manifest</div>'
    target = (base / src).resolve()
    if not target.exists():
        return '<div class="missing">missing image: %s</div>' % esc(src)
    ref = dataUri(target) if inline else esc(src)
    return '<img src="%s" alt="%s" loading="lazy">' % (ref, esc(alt))


def figure(src, base, inline, label, cls, alt):
    return (
        '<figure><figcaption class="%s">%s</figcaption>'
        '<div class="frame">%s</div></figure>' % (cls, esc(label), imgTag(src, base, inline, alt))
    )


def renderShot(shot, base, inline, surfaceName):
    viewport = shot.get("viewport", "")
    before = shot.get("before")
    after = shot.get("after") or shot.get("image")
    added = shot.get("added") or not before
    parts = ['<div class="shot">']
    if viewport:
        parts.append('<p class="vp">%s</p>' % esc(viewport))
    parts.append('<div class="pair%s">' % ("" if before else " single"))
    if before:
        parts.append(figure(before, base, inline, "before", "before",
                            "%s before, %s" % (surfaceName, viewport)))
        parts.append(figure(after, base, inline, "after", "after",
                            "%s after, %s" % (surfaceName, viewport)))
    else:
        label = "added - no before" if added else "current"
        parts.append(figure(after, base, inline, label, "added",
                            "%s, %s" % (surfaceName, viewport)))
    parts.append("</div></div>")
    return "".join(parts)


def renderSurface(surface, base, inline):
    name = surface.get("name", "Untitled surface")
    parts = ['<section class="surface"><h2>%s</h2>' % esc(name)]
    if surface.get("route"):
        parts.append('<p class="route">%s</p>' % esc(surface["route"]))
    if surface.get("note"):
        parts.append('<p class="note">%s</p>' % esc(surface["note"]))
    for shot in surface.get("shots", []):
        parts.append(renderShot(shot, base, inline, name))
    parts.append("</section>")
    return "".join(parts)


def renderPage(manifest, base, inline):
    pr = manifest.get("pr")
    title = manifest.get("title", "Design evidence")
    heading = esc(title)
    if pr:
        heading = '<span class="num">#%s</span> %s' % (esc(pr), heading)

    head = ['<div class="wrap"><header>',
            '<p class="eyebrow">Design gate - founder review</p>',
            "<h1>%s</h1>" % heading]
    if manifest.get("summary"):
        head.append('<p class="summary">%s</p>' % esc(manifest["summary"]))
    meta = ["Captured %s" % date.today().isoformat()]
    if manifest.get("branch"):
        meta.append("branch <code>%s</code>" % esc(manifest["branch"]))
    metaLine = " &middot; ".join(meta)
    if manifest.get("url"):
        metaLine += ' &middot; <a href="%s">%s</a>' % (esc(manifest["url"]), esc(manifest["url"]))
    head.append('<p class="meta">%s</p>' % metaLine)
    head.append("</header>")

    gaps = manifest.get("gaps") or []
    if gaps:
        head.append('<div class="gaps"><h2>Stated gaps</h2><ul>')
        head.extend("<li>%s</li>" % esc(g) for g in gaps)
        head.append("</ul></div>")

    body = [renderSurface(s, base, inline) for s in manifest.get("surfaces", [])]
    if not body:
        body = ['<section class="surface"><h2>No surfaces in manifest</h2></section>']

    foot = ("<footer>Session-local evidence. Not committed to the repository. "
            "Generated by <code>/design-gate</code>.</footer></div>")

    return (
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        "<title>Design gate - %s</title>\n<style>%s</style>\n%s"
        % (esc(title), CSS, "".join(head) + "".join(body) + foot)
    )


def main():
    ap = argparse.ArgumentParser(description="Build a design-gate evidence page.")
    ap.add_argument("manifest")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--inline", action="store_true",
                    help="embed images as data URIs instead of relative paths")
    args = ap.parse_args()

    manifestPath = Path(args.manifest).resolve()
    try:
        manifest = json.loads(manifestPath.read_text())
    except (OSError, ValueError) as err:
        print("cannot read manifest: %s" % err, file=sys.stderr)
        return 2
    if not isinstance(manifest, dict):
        print("manifest must be a JSON object", file=sys.stderr)
        return 2

    base = manifestPath.parent
    out = Path(args.out).resolve() if args.out else base / "evidence.html"
    out.write_text(renderPage(manifest, base, args.inline))

    shots = sum(len(s.get("shots", [])) for s in manifest.get("surfaces", []))
    print("%s (%d surfaces, %d shots, %s)"
          % (out, len(manifest.get("surfaces", [])), shots,
             "inlined" if args.inline else "relative paths"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
