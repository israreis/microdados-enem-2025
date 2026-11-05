"""Gera o fundo das páginas do relatório (PNG para o Power BI) e uma prévia em HTML.

O Power BI não renderiza HTML nos visuais nativos. A técnica usada é desenhar
a "moldura" da página (cabeçalho, cartões, painéis, barras de destaque) como
imagem de fundo e colocar os visuais por cima, com fundo transparente.

Uso:
    python projeto-1-analise-powerbi/layout/gerar_fundos.py

Saída (nesta pasta):
    fundo_paginaN.png      -> Formatar página > Plano de fundo da tela > Imagem
    layout_paginaN.html    -> prévia no navegador, com as posições de cada visual
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent
LARGURA, ALTURA = 1920, 1080
ESCALA = 2  # desenha em 2x para bordas suaves e reduz no final

CORES = {
    "pagina": "#F4F6FA",
    "cabecalho": "#0B2545",
    "painel": "#FFFFFF",
    "borda": "#E5E7EB",
    "azul": "#1D4E89",
    "verde": "#2A9D8F",
    "coral": "#E76F51",
    "ambar": "#E9A23B",
}

# (nome, horizontal, vertical, largura, altura, tipo, cor de destaque)
PAGINA1 = [
    ("Cabeçalho (título em caixa de texto)", 0, 0, 1920, 108, "cabecalho", None),
    ("Segmentador área (botões)", 36, 132, 1140, 66, "livre", None),
    ("Segmentador região (suspenso)", 1200, 132, 330, 66, "caixa", None),
    ("Segmentador rede (suspenso)", 1554, 132, 330, 66, "caixa", None),
    ("Cartão Inscritos", 36, 222, 444, 156, "cartao", "azul"),
    ("Cartão Taxa de presença", 504, 222, 444, 156, "cartao", "verde"),
    ("Cartão Abstenção dia 1", 972, 222, 444, 156, "cartao", "coral"),
    ("Cartão Abstenção dia 2", 1440, 222, 444, 156, "cartao", "coral"),
    ("Gráfico de colunas: média por prova", 36, 402, 900, 642, "painel", None),
    ("Gráfico de barras: média por UF", 960, 402, 924, 642, "painel", None),
]

PAGINA2 = [
    ("Cabeçalho (título em caixa de texto)", 0, 0, 1920, 108, "cabecalho", None),
    ("Segmentador área (botões, sincronizado)", 36, 132, 1470, 66, "livre", None),
    ("Segmentador região (suspenso, sincronizado)", 1530, 132, 354, 66, "caixa", None),
    ("Cartão Média pública", 36, 222, 444, 156, "cartao", "verde"),
    ("Cartão Média privada", 504, 222, 444, 156, "cartao", "azul"),
    ("Cartão Diferença privada − pública", 972, 222, 444, 156, "cartao", "coral"),
    ("Cartão UF com maior diferença", 1440, 222, 444, 156, "cartao", "ambar"),
    ("Barras: diferença por UF", 36, 402, 900, 642, "painel", None),
    ("Colunas: média por rede", 960, 402, 924, 309, "painel", None),
    ("Linhas: distribuição das notas", 960, 735, 924, 309, "painel", None),
]

PAGINAS = {1: PAGINA1, 2: PAGINA2}

RAIO = 12
DESTAQUE = 6  # altura da barra colorida no topo dos cartões


def desenhar_png(elementos, saida: Path) -> None:
    s = ESCALA
    img = Image.new("RGB", (LARGURA * s, ALTURA * s), CORES["pagina"])
    d = ImageDraw.Draw(img)
    for _, x, y, w, h, tipo, destaque in elementos:
        caixa = [x * s, y * s, (x + w) * s - 1, (y + h) * s - 1]
        if tipo == "cabecalho":
            d.rectangle(caixa, fill=CORES["cabecalho"])
        elif tipo == "caixa":
            # moldura dos dropdowns, no mesmo estilo dos botões de área
            d.rounded_rectangle(caixa, radius=RAIO * s, fill=CORES["painel"],
                                outline=CORES["borda"], width=2)
        elif tipo in ("painel", "cartao"):
            d.rounded_rectangle(caixa, radius=RAIO * s, fill=CORES["painel"],
                                outline=CORES["borda"], width=2)
            if tipo == "cartao" and destaque:
                # barra de destaque: topo arredondado, base reta
                d.rounded_rectangle([x * s, y * s, (x + w) * s - 1, (y + DESTAQUE + RAIO) * s],
                                    radius=RAIO * s, fill=CORES[destaque])
                d.rectangle([x * s, (y + DESTAQUE) * s, (x + w) * s - 1, (y + DESTAQUE + RAIO) * s],
                            fill=CORES["painel"])
                d.line([x * s, (y + DESTAQUE) * s, x * s, (y + DESTAQUE + RAIO) * s],
                       fill=CORES["borda"], width=2)
                d.line([(x + w) * s - 1, (y + DESTAQUE) * s, (x + w) * s - 1, (y + DESTAQUE + RAIO) * s],
                       fill=CORES["borda"], width=2)
    img.resize((LARGURA, ALTURA), Image.LANCZOS).save(saida, optimize=True)


def gerar_html(elementos, png: str, saida: Path) -> None:
    caixas = []
    for nome, x, y, w, h, tipo, _ in elementos:
        caixas.append(
            f'<div class="v {tipo}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
            f'<span>{nome}<br><small>H {x} · V {y} · L {w} · A {h}</small></span></div>'
        )
    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Layout página 1</title>
<style>
  body {{ margin:0; background:#1f2937; font-family:'Segoe UI',system-ui,sans-serif; }}
  .wrap {{ transform-origin:top left; }}
  .canvas {{ position:relative; width:{LARGURA}px; height:{ALTURA}px;
             background:url('{png}') no-repeat; background-size:100% 100%; }}
  .v {{ position:absolute; box-sizing:border-box; border:2px dashed rgba(29,78,137,.45);
        border-radius:12px; display:flex; align-items:center; justify-content:center;
        text-align:center; color:#1D4E89; font-size:18px; }}
  .v.cabecalho {{ color:#9FB3C8; border-color:rgba(159,179,200,.5); border-radius:0; }}
  .v small {{ font-size:14px; opacity:.75; }}
  .legenda {{ color:#e5e7eb; padding:12px 16px; font-size:14px; }}
</style></head><body>
<div class="legenda">Prévia do layout em 1920 × 1080. A imagem de fundo é o PNG; as caixas
tracejadas mostram onde posicionar cada visual (H = horizontal, V = vertical, L = largura, A = altura).</div>
<div class="wrap" id="wrap"><div class="canvas">
{chr(10).join(caixas)}
</div></div>
<script>
  function ajustar() {{
    const k = Math.min(1, (window.innerWidth - 16) / {LARGURA});
    const w = document.getElementById('wrap');
    w.style.transform = 'scale(' + k + ')';
    w.style.height = ({ALTURA} * k) + 'px';
  }}
  window.addEventListener('resize', ajustar); ajustar();
</script>
</body></html>
"""
    saida.write_text(html, encoding="utf-8")


def main() -> None:
    for n, elementos in PAGINAS.items():
        png = AQUI / f"fundo_pagina{n}.png"
        desenhar_png(elementos, png)
        gerar_html(elementos, png.name, AQUI / f"layout_pagina{n}.html")
        print(f"Gerados: {png.name} e layout_pagina{n}.html em {AQUI}")


if __name__ == "__main__":
    main()
