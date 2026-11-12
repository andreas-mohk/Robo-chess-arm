"""Collect the generated build documents into docs/ and write docs/build-docs.html.

  python3 tools/make_docs_page.py   (after cad/guide.py, cad/drawings.py and electronics/*.py)
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SRC = {"guide": ROOT / "cad/out/guide", "drawings": ROOT / "cad/out/drawings", "electronics": ROOT / "electronics/out"}


def copy():
    for k, src in SRC.items():
        dst = DOCS / k
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True)
        for f in src.iterdir():
            if f.suffix in (".svg", ".pdf", ".md", ".json"):
                shutil.copy2(f, dst / f.name)


def md_tables_to_html(md):
    """Small Markdown subset: headings, tables, bullet and numbered lists, paragraphs, inline code."""
    out, rows, lst = [], [], None
    def inline(s):
        s = html.escape(s)
        return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    def flush_table():
        nonlocal rows
        if rows:
            head, body = rows[0], [r for r in rows[2:]]
            out.append("<div class='tbl'><table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table></div>")
            rows = []
    def flush_list():
        nonlocal lst
        if lst:
            tag, items = lst
            out.append(f"<{tag}>" + "".join(f"<li>{inline(i)}</li>" for i in items) + f"</{tag}>")
            lst = None
    for line in md.splitlines():
        if line.startswith("|"):
            flush_list()
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
            continue
        flush_table()
        m = re.match(r"^(\d+)\. (.*)", line)
        if line.startswith("- ") or m:
            tag = "ol" if m else "ul"
            item = m.group(2) if m else line[2:]
            if not lst or lst[0] != tag:
                flush_list()
                lst = (tag, [])
            lst[1].append(item)
            continue
        flush_list()
        if line.startswith("## "):
            out.append(f"<h3>{inline(line[3:])}</h3>")
        elif line.startswith("# "):
            continue
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
    flush_table()
    flush_list()
    return "\n".join(out)


def page():
    steps = json.loads((DOCS / "guide/steps.json").read_text())
    guide_pages = [{"file": "guide/step_00a_cover.svg", "title": "Cover", "no": 0},
                   {"file": "guide/step_00b_inventory.svg", "title": "Before you start", "no": 0}]
    guide_pages += [{"file": f"guide/step_{s['no']:02d}.svg", "title": s["title"], "no": s["no"], "repeat": s["repeat"]} for s in steps]
    sheets = sorted(p.name for p in (DOCS / "drawings").glob("*.svg"))
    def sheet_title(n):
        t = n[:-4]
        t = re.sub(r"^\d+_", "", t)
        t = re.sub(r"^P\d+_", "", t)
        return t.replace("_", " ")
    drawings = [{"file": f"drawings/{n}", "title": sheet_title(n), "no": int(n.split("_")[0])} for n in sheets]
    pinmap = md_tables_to_html((DOCS / "electronics/pinmap.md").read_text())
    wiring = md_tables_to_html((DOCS / "electronics/perfboard_wiring.md").read_text())
    data = json.dumps({"guide": guide_pages, "drawings": drawings})
    tpl = (ROOT / "tools/build_docs_template.html").read_text()
    out = tpl.replace("/*DATA*/null", data).replace("<!--PINMAP-->", pinmap).replace("<!--WIRING-->", wiring)
    (DOCS / "build-docs.html").write_text(out)
    print(f"docs page: {len(guide_pages)} guide pages, {len(drawings)} drawing sheets")


if __name__ == "__main__":
    copy()
    page()
