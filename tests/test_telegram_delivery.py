"""Tests de la entrega a Telegram: fragmentado HTML válido dentro del límite de la API."""

import re

from src.telegram_notifier import CHUNK_LIMIT, split_html_safe


def _tags_balanced(fragment: str) -> bool:
    """Verifica que todo tag abierto en el fragmento quede cerrado dentro del mismo."""
    stack = []
    for closing, name in re.findall(r"<(/?)([a-zA-Z][a-zA-Z0-9-]*)(?:\s[^>]*)?>", fragment):
        name = name.lower()
        if closing:
            if not stack or stack.pop() != name:
                return False
        elif name != "br":
            stack.append(name)
    return not stack


class TestSplitHtmlSafe:
    def test_short_text_is_not_split(self):
        assert split_html_safe("<b>corto</b>") == ["<b>corto</b>"]

    def test_every_chunk_respects_the_limit(self):
        text = "<pre>" + ("linea de contenido tecnico\n" * 600) + "</pre>"
        for chunk in split_html_safe(text, CHUNK_LIMIT):
            assert len(chunk) <= CHUNK_LIMIT

    def test_limit_holds_without_line_breaks(self):
        """Regresión: la reserva se calculaba con el stack previo al cuerpo.

        Con saltos de línea el corte caía antes del budget y el defecto quedaba oculto;
        sin ellos el sufijo </pre> empujaba el fragmento a 3806 caracteres.
        """
        text = "<pre>" + ("x" * 9000) + "</pre>"
        for chunk in split_html_safe(text, CHUNK_LIMIT):
            assert len(chunk) <= CHUNK_LIMIT

    def test_deep_nesting_terminates(self):
        """Regresión: con el prefijo comiéndose el budget, `pos` no avanzaba nunca."""
        deep = "".join(f"<b{i % 10}>" for i in range(700))
        chunks = split_html_safe(deep + ("contenido de relleno " * 500), CHUNK_LIMIT)
        assert chunks
        assert "".join(chunks)  # terminó: sin esto el test colgaría

    def test_reopened_tags_keep_their_attributes(self):
        """Regresión: `<a href="...">` se reabría como `<a>`, que Telegram rechaza."""
        href = '<a href="https://ejemplo.com/una/url/larga">'
        chunks = split_html_safe(href + ("palabra " * 700) + "</a>", CHUNK_LIMIT)
        assert len(chunks) > 1
        assert chunks[1].startswith(href)

    def test_void_tags_are_not_stacked(self):
        chunks = split_html_safe("<b>" + ("texto <br> mas texto " * 400) + "</b>", CHUNK_LIMIT)
        for chunk in chunks:
            assert "</br>" not in chunk

    def test_never_cuts_inside_an_html_entity(self):
        """Cortar a los 3800 chars partía entidades como &amp; y Telegram rechazaba el mensaje."""
        text = "<pre>" + ("dato &amp; valor &lt;tag&gt; " * 400) + "</pre>"
        for chunk in split_html_safe(text, CHUNK_LIMIT):
            for match in re.finditer(r"&[a-zA-Z#0-9]*", chunk):
                tail = chunk[match.end():match.end() + 1]
                assert tail == ";" or not match.group(0)[1:], f"entidad partida: {match.group(0)!r}"

    def test_never_cuts_inside_a_tag(self):
        text = "".join(f"<b>item {i}</b> con texto de relleno suficiente. " for i in range(400))
        for chunk in split_html_safe(text, CHUNK_LIMIT):
            assert chunk.count("<") == chunk.count(">")

    def test_each_chunk_is_balanced(self):
        text = "<pre>" + ("una linea larga de contenido tecnico repetido\n" * 400) + "</pre>"
        for chunk in split_html_safe(text, CHUNK_LIMIT):
            assert _tags_balanced(chunk), f"fragmento desbalanceado: {chunk[:80]!r}"

    def test_content_survives_the_split(self):
        body = "".join(f"linea numero {i}\n" for i in range(500))
        chunks = split_html_safe(f"<pre>{body}</pre>", CHUNK_LIMIT)
        rebuilt = "".join(re.sub(r"</?pre>", "", c) for c in chunks)
        assert "linea numero 0" in rebuilt
        assert "linea numero 499" in rebuilt

    def test_prefers_line_boundaries(self):
        text = "".join(f"linea {i}\n" for i in range(900))
        chunks = split_html_safe(text, CHUNK_LIMIT)
        assert len(chunks) > 1
        assert chunks[0].endswith("\n")
