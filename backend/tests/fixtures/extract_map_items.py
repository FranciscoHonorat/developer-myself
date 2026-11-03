"""Extrai os itens do PDF do mapa para `mapa_itens.txt` (rodar quando o PDF mudar).

Uso: pdftotext -layout "Docs/Mapa de conteúdos ....pdf" - | python extract_map_items.py
"""

import re
import sys

text = sys.stdin.read()
body = text[text.index("1. Fundamentos comuns\nÉ") : text.index("7. Onde praticar")]
items: list[str] = []
block = ""
for raw in body.splitlines():
    line = raw.strip()
    if not line or line.startswith(("Page ", "Mapa de conte")):
        continue
    if not raw.startswith(" "):  # título de seção/bloco (parágrafos longos são descrição)
        if re.match(r"^\d\. ", line) or "[" in line or len(line) < 60:
            block = line
        continue
    if items and (line[0].islower() or line[0] in "(") and not line.startswith("go "):
        items[-1] += " " + line  # continuação de uma linha quebrada no PDF
        continue
    items.append(f"{block} :: {line}")
sys.stdout.write("\n".join(items) + "\n")
