from pathlib import Path
import re

from markupsafe import Markup, escape

from odoo import http
from odoo.http import request


class DoorAndDoorSalesNewDocsController(http.Controller):
    _DOCS_MODULE_DIR = Path(__file__).resolve().parents[2] / "doorandoor_sales_new"
    _DOCS_DIR = _DOCS_MODULE_DIR / "docs"
    _DOCS_ROUTE = "/doorandoor-sales-new/docs"
    _PUBLISHED_DOCS = [
        "presentation_and_training_guide.md",
        "invoice_sale_fulfillment_flow_explained.md",
        "payment_release_stock_mrp_delivery_flow_explained.md",
        "pickup_order_flow_explained.md",
    ]

    def _slugify(self, value):
        value = (value or "").strip().lower()
        value = re.sub(r"[^a-z0-9]+", "-", value)
        return value.strip("-")

    def _extract_title(self, text, fallback):
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return fallback

    def _rewrite_markdown_links(self, text):
        docs_slug_map = {
            path.name: self._slugify(path.stem)
            for path in self._get_published_doc_paths()
        }

        def _replace(match):
            label = match.group("label")
            target = match.group("target").strip()
            doc_match = re.search(r"/addons/doorandoor_sales_new/docs/([^/)]+\.md)(?::\d+)?$", target)
            if doc_match:
                filename = doc_match.group(1)
                slug = docs_slug_map.get(filename)
                if slug:
                    return f"[{label}]({self._DOCS_ROUTE}/{slug})"

            if target.startswith("/home/") or target.startswith("file://"):
                return f"`{label}`"

            return match.group(0)

        return re.sub(r"\[(?P<label>[^\]]+)\]\((?P<target>[^)]+)\)", _replace, text)

    def _format_inline_markdown(self, text):
        escaped = escape(text)
        escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
        escaped = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2">\1</a>',
            escaped,
        )
        return escaped

    def _render_simple_markdown(self, text):
        lines = text.splitlines()
        html = []
        paragraph = []
        in_list = False
        in_code = False
        code_lines = []

        def flush_paragraph():
            nonlocal paragraph
            if paragraph:
                html.append(f"<p>{self._format_inline_markdown(' '.join(paragraph))}</p>")
                paragraph = []

        def close_list():
            nonlocal in_list
            if in_list:
                html.append("</ul>")
                in_list = False

        def flush_code():
            nonlocal in_code, code_lines
            if in_code:
                html.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False

        for raw_line in lines:
            line = raw_line.rstrip()
            stripped = line.strip()

            if stripped.startswith("```"):
                flush_paragraph()
                close_list()
                if in_code:
                    flush_code()
                else:
                    in_code = True
                continue

            if in_code:
                code_lines.append(line)
                continue

            if not stripped:
                flush_paragraph()
                close_list()
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if heading_match:
                flush_paragraph()
                close_list()
                level = len(heading_match.group(1))
                content = self._format_inline_markdown(heading_match.group(2))
                html.append(f"<h{level}>{content}</h{level}>")
                continue

            if re.match(r"^[-*]\s+", stripped):
                flush_paragraph()
                if not in_list:
                    html.append("<ul>")
                    in_list = True
                item = re.sub(r"^[-*]\s+", "", stripped)
                html.append(f"<li>{self._format_inline_markdown(item)}</li>")
                continue

            if re.match(r"^\d+\.\s+", stripped):
                flush_paragraph()
                if in_list:
                    close_list()
                html.append(f"<p>{self._format_inline_markdown(stripped)}</p>")
                continue

            paragraph.append(stripped)

        flush_paragraph()
        close_list()
        flush_code()
        return "\n".join(html)

    def _build_markdown(self, text):
        return self._render_simple_markdown(text)

    def _get_published_doc_paths(self):
        paths = []
        for filename in self._PUBLISHED_DOCS:
            path = self._DOCS_DIR / filename
            if path.exists():
                paths.append(path)
        return paths

    def _get_doc_files(self):
        if not self._DOCS_DIR.exists():
            return []

        docs = []
        for path in self._get_published_doc_paths():
            text = path.read_text(encoding="utf-8")
            title = self._extract_title(text, path.stem.replace("_", " ").title())
            slug = self._slugify(path.stem)
            docs.append(
                {
                    "filename": path.name,
                    "name": path.stem,
                    "title": title,
                    "slug": slug,
                    "path": path,
                    "summary": self._extract_summary(text),
                }
            )

        order_map = {name: index for index, name in enumerate(self._PUBLISHED_DOCS)}
        docs.sort(key=lambda doc: (order_map.get(doc["filename"], len(self._PUBLISHED_DOCS)), doc["title"].lower()))
        return docs

    def _extract_summary(self, text):
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append(stripped)
            if len(" ".join(lines)) >= 180:
                break
        summary = " ".join(lines)
        return summary[:180].rstrip() + ("..." if len(summary) > 180 else "")

    def _get_doc_by_slug(self, slug):
        for doc in self._get_doc_files():
            if doc["slug"] == slug:
                return doc
        return None

    @http.route(_DOCS_ROUTE, type="http", auth="public", website=True, sitemap=True)
    def docs_home(self, **kwargs):
        docs = self._get_doc_files()
        return request.render(
            "doorandoor_sales_new_docs_website.docs_index",
            {
                "docs": docs,
                "docs_route": self._DOCS_ROUTE,
            },
        )

    @http.route(f"{_DOCS_ROUTE}/<string:doc_slug>", type="http", auth="public", website=True, sitemap=True)
    def docs_page(self, doc_slug, **kwargs):
        doc = self._get_doc_by_slug(doc_slug)
        if not doc:
            return request.not_found()

        text = self._rewrite_markdown_links(doc["path"].read_text(encoding="utf-8"))
        html = self._build_markdown(text)
        docs = self._get_doc_files()
        current_index = next((index for index, item in enumerate(docs) if item["slug"] == doc_slug), 0)
        previous_doc = docs[current_index - 1] if current_index > 0 else None
        next_doc = docs[current_index + 1] if current_index < len(docs) - 1 else None

        return request.render(
            "doorandoor_sales_new_docs_website.docs_page",
            {
                "doc": doc,
                "doc_html": Markup(html),
                "docs": docs,
                "docs_route": self._DOCS_ROUTE,
                "previous_doc": previous_doc,
                "next_doc": next_doc,
            },
        )
