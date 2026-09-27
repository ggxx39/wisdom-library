#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone zero-dependency EPUB 3 compiler for Wisdom Library.
Produces reflowable EPUB 3 publications formatted with iPhone Reader CSS.
"""

import os
import sys
import re
import html
import zipfile
from pathlib import Path

def compile_epub_from_markdown(md_file: Path, cover_file: Path, css_file: Path, out_epub: Path, title: str, author: str):
    text = md_file.read_text(encoding="utf-8")
    
    # Strip frontmatter
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
            
    # Split by level 1 headers
    raw_chapters = re.split(r"(?m)^# (.+)$", text)
    chapters = []
    if len(raw_chapters) > 1:
        preamble = raw_chapters[0].strip()
        if preamble:
            chapters.append(("全书概览与目录", preamble))
        for i in range(1, len(raw_chapters), 2):
            ch_title = raw_chapters[i].strip()
            ch_body = raw_chapters[i+1].strip() if i+1 < len(raw_chapters) else ""
            chapters.append((ch_title, ch_body))
    else:
        chapters.append(("正文", text.strip()))

    def md_to_html(md_content: str) -> str:
        lines = md_content.split("\n")
        html_out = []
        p_lines = []
        
        def flush_p():
            nonlocal p_lines
            if p_lines:
                c = " ".join(p_lines).strip()
                c = html.escape(c)
                c = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", c)
                c = re.sub(r"\*(.+?)\*", r"<em>\1</em>", c)
                html_out.append(f"<p>{c}</p>")
                p_lines.clear()

        for line in lines:
            line_str = line.strip()
            if not line_str:
                flush_p()
                continue
            if line_str.startswith("### "):
                flush_p()
                h_text = html.escape(line_str[4:].strip())
                html_out.append(f"<h3>{h_text}</h3>")
            elif line_str.startswith("## "):
                flush_p()
                h_text = html.escape(line_str[3:].strip())
                html_out.append(f"<h2>{h_text}</h2>")
            elif line_str.startswith("# "):
                flush_p()
                h_text = html.escape(line_str[2:].strip())
                html_out.append(f"<h1>{h_text}</h1>")
            elif line_str.startswith("> "):
                flush_p()
                b_text = html.escape(line_str[2:].strip())
                html_out.append(f"<blockquote><p>{b_text}</p></blockquote>")
            elif line_str.startswith("- "):
                flush_p()
                li_text = html.escape(line_str[2:].strip())
                html_out.append(f"<ul><li>{li_text}</li></ul>")
            else:
                p_lines.append(line_str)
        flush_p()
        return "\n".join(html_out)

    with zipfile.ZipFile(out_epub, "w", zipfile.ZIP_DEFLATED) as z:
        # 1. mimetype (MUST be uncompressed)
        z.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
        
        # 2. container.xml
        container = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
        z.writestr("META-INF/container.xml", container)
        
        # 3. CSS
        css_content = css_file.read_text(encoding="utf-8") if css_file.exists() else ""
        z.writestr("OEBPS/style.css", css_content)
        
        # 4. Cover
        manifest_items = []
        spine_items = []
        nav_links = []
        has_cover = cover_file.exists()
        
        if has_cover:
            z.write(cover_file, "OEBPS/cover.jpg")
            cover_html = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Cover</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
<body style="margin:0;padding:0;text-align:center;">
<img src="cover.jpg" alt="Cover" style="max-width:100%;height:auto;"/>
</body>
</html>"""
            z.writestr("OEBPS/cover.xhtml", cover_html)
            manifest_items.append('<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>')
            manifest_items.append('<item id="cover-img" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>')
            spine_items.append('<itemref idref="cover"/>')
            
        manifest_items.append('<item id="style" href="style.css" media-type="text/css"/>')
        manifest_items.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
        
        for idx, (ch_t, ch_b) in enumerate(chapters):
            ch_id = f"ch_{idx+1}"
            ch_filename = f"chapter_{idx+1}.xhtml"
            body_html = md_to_html(ch_b)
            ch_doc = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>{html.escape(ch_t)}</title>
  <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
  <h1>{html.escape(ch_t)}</h1>
  {body_html}
</body>
</html>"""
            z.writestr(f"OEBPS/{ch_filename}", ch_doc)
            manifest_items.append(f'<item id="{ch_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{ch_id}"/>')
            nav_links.append(f'<li><a href="{ch_filename}">{html.escape(ch_t)}</a></li>')
            
        nav_doc = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>目录</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
<body>
<nav epub:type="toc" id="toc">
  <h1>目录</h1>
  <ol>
    {"".join(nav_links)}
  </ol>
</nav>
</body>
</html>"""
        z.writestr("OEBPS/nav.xhtml", nav_doc)
        
        opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="pub-id" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">urn:uuid:wisdom-library-rational-choice-2026</dc:identifier>
    <dc:title>{html.escape(title)}</dc:title>
    <dc:creator>{html.escape(author)}</dc:creator>
    <dc:language>zh-CN</dc:language>
  </metadata>
  <manifest>
    {"".join(manifest_items)}
  </manifest>
  <spine>
    {"".join(spine_items)}
  </spine>
</package>"""
        z.writestr("OEBPS/content.opf", opf)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: build_epub.py <md_file> <cover_file> <css_file> <out_epub> [title] [author]")
        sys.exit(1)
    md = Path(sys.argv[1])
    cov = Path(sys.argv[2])
    css = Path(sys.argv[3])
    out = Path(sys.argv[4])
    t = sys.argv[5] if len(sys.argv) > 5 else "Publication"
    a = sys.argv[6] if len(sys.argv) > 6 else "Wisdom Library"
    compile_epub_from_markdown(md, cov, css, out, t, a)
    print(f"✅ Generated {out} ({out.stat().st_size / 1024:.1f} KB)")
