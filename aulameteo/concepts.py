"""Concept cards: Markdown files with YAML front matter in concepts/."""
import re

import markdown
import yaml

from . import config

LINK_RE = re.compile(r"\[\[([a-z0-9-]+)(?:\|([^\]]+))?\]\]")
VIEW_RE = re.compile(r"^#ver:-?\d+(\.\d+)?,-?\d+(\.\d+)?,\d(\.\d+)?,[a-z0-9+]+(,\d{1,2})?$")


def _split(text):
    _, front, body = text.split("---", 2)
    return yaml.safe_load(front), body.strip()


def load_cards():
    cards = []
    for path in sorted(config.CONCEPTS.glob("*.md")):
        if path.name.startswith("_"):
            continue
        meta, body = _split(path.read_text(encoding="utf-8"))
        # Card sections sit under the card title, one level down.
        cards.append({**meta, "body": re.sub(r"^## ", "### ", body, flags=re.M)})
    return sorted(cards, key=lambda c: c["order"])


def load_intro():
    meta, body = _split((config.CONCEPTS / "_intro.md").read_text(encoding="utf-8"))
    return meta, body


def render(md_text, titles, root="", anchors=False):
    """Markdown -> HTML, turning [[slug|text]] into concept links and dropping unknown slugs.

    `titles` maps slug -> title. Links point to the concepts page (`root` is the relative path to the
    site root); day pages intercept them to open the card in a drawer. With `anchors`, they point to
    the card on the same page. Map links (#ver:...) that do not parse are reduced to their text.
    """
    def concept(m):
        slug, text = m.group(1), m.group(2) or m.group(1).replace("-", " ")
        if slug not in titles:
            return text
        href = f"#{slug}" if anchors else f"{root}conceptos.html#{slug}"
        return f'<a class="concept" href="{href}" data-concept="{slug}">{text}</a>'

    html = markdown.markdown(LINK_RE.sub(concept, md_text), extensions=["sane_lists"])

    def view(m):
        href, text = m.group(1), m.group(2)
        if VIEW_RE.match(href):
            return f'<a class="view" href="{href}">{text}</a>'
        return text

    return re.sub(r'<a href="(#ver:[^"]*)">(.*?)</a>', view, html)
