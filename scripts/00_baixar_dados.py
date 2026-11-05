"""Baixa (pelo navegador) e extrai os microdados do ENEM 2025 para data/raw/.

Uso:
    python scripts/00_baixar_dados.py
    python scripts/00_baixar_dados.py --zip "C:/Users/voce/Downloads/microdados_enem_2025.zip"
    python scripts/00_baixar_dados.py --pasta "D:/Downloads"   # se seus downloads vão para outro lugar

Como funciona:
1. Abre o link do zip no seu navegador padrão (o servidor do INEP derruba
   downloads feitos direto pelo Python, mas aceita o navegador).
2. Fica vigiando a pasta Downloads até o arquivo terminar de baixar.
3. Extrai os CSVs em data/raw/.

O zip do INEP usa compressão Deflate64, que o módulo zipfile do Python não
abre. Por isso a extração tenta, nesta ordem: Python, 7-Zip (se instalado) e
o descompactador do próprio Windows (o mesmo do Explorador de Arquivos).
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
import webbrowser
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from enem import DATA_RAW  # noqa: E402

URL = "https://download.inep.gov.br/microdados/microdados_enem_2025.zip"
PADRAO_NOME = "microdados_enem_2025*.zip"          # o navegador pode criar "... (1).zip"
SUFIXOS_PARCIAIS = (".crdownload", ".part", ".partial", ".download", ".tmp")
ESPERADOS = ["RESULTADOS_2025.csv", "PARTICIPANTES_2025.csv", "ITENS_PROVA_2025.csv"]
ESPERA_MAX = 3 * 60 * 60                            # 3 horas
INTERVALO = 5


# ---------------------------------------------------------------- download
def pastas_download(extra: Path | None) -> list[Path]:
    """Lugares onde o navegador costuma salvar no Windows (e Linux/Mac)."""
    home = Path.home()
    candidatas = [extra, home / "Downloads", home / "OneDrive" / "Downloads", DATA_RAW]
    vistas, saida = set(), []
    for p in candidatas:
        if p and p.exists() and p.resolve() not in vistas:
            vistas.add(p.resolve())
            saida.append(p)
    return saida


def zips_existentes(pastas: list[Path]) -> list[Path]:
    achados = [z for p in pastas for z in p.glob(PADRAO_NOME)]
    return sorted(achados, key=lambda z: z.stat().st_mtime, reverse=True)


def parciais(pastas: list[Path]) -> list[Path]:
    """Arquivos temporários de download mexidos no último minuto
    (Chrome/Edge: .crdownload, Firefox: .part)."""
    agora = time.time()
    return [f for p in pastas for f in p.iterdir()
            if f.suffix.lower() in SUFIXOS_PARCIAIS and agora - f.stat().st_mtime < 60]


def esperar_download(pastas: list[Path], antes: set[Path]) -> Path:
    """Espera aparecer um zip novo e o tamanho dele parar de mudar."""
    print("Aguardando o download terminar (Ctrl+C para cancelar)...")
    print("  vigiando:", ", ".join(str(p) for p in pastas))
    inicio = time.time()
    ultimo_tam, estavel_desde = -1, None
    while time.time() - inicio < ESPERA_MAX:
        novos = [z for z in zips_existentes(pastas) if z not in antes]
        if novos and not parciais(pastas):
            z = novos[0]
            tam = z.stat().st_size
            if tam == ultimo_tam and tam > 0:
                if estavel_desde and time.time() - estavel_desde >= 10:
                    print(f"\n  download concluído: {z} ({tam / 1e9:.2f} GB)")
                    return z
            else:
                ultimo_tam, estavel_desde = tam, time.time()
        else:
            tam = max((f.stat().st_size for f in parciais(pastas)), default=0)
            print(f"\r  {time.time() - inicio:5.0f}s  baixado até agora: {tam / 1e9:.2f} GB   ",
                  end="", flush=True)
        time.sleep(INTERVALO)
    sys.exit("\nTempo esgotado. Quando o download terminar, rode: "
             "python scripts/00_baixar_dados.py --zip CAMINHO_DO_ZIP")


# ---------------------------------------------------------------- extração
def zip_valido(caminho: Path) -> bool:
    """Confere só o índice do zip (rápido e funciona com qualquer compressão)."""
    try:
        with zipfile.ZipFile(caminho) as z:
            nomes = {Path(n).name.upper() for n in z.namelist()}
        return "RESULTADOS_2025.CSV" in nomes
    except (zipfile.BadZipFile, OSError):
        return False


def extraido() -> bool:
    return all(list(DATA_RAW.rglob(n)) for n in ESPERADOS)


def extrair_python(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(DATA_RAW)


def extrair_7zip(zip_path: Path) -> None:
    candidatos = [shutil.which("7z"), shutil.which("7z.exe"),
                  r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"]
    exe = next((c for c in candidatos if c and Path(c).exists()), None)
    if not exe:
        raise RuntimeError("7-Zip não instalado")
    subprocess.run([exe, "x", str(zip_path), f"-o{DATA_RAW}", "-y"], check=True)


def extrair_windows(zip_path: Path) -> None:
    """Usa o descompactador do Explorador de Arquivos, que entende Deflate64."""
    if sys.platform != "win32":
        raise RuntimeError("só disponível no Windows")
    destino = DATA_RAW.resolve()
    origem = zip_path.resolve()
    ps = (
        "$s = New-Object -ComObject Shell.Application; "
        f"$s.NameSpace('{destino}').CopyHere($s.NameSpace('{origem}').Items(), 16)"
    )
    print("  (o Windows pode mostrar uma janela de progresso; deixe terminar)")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    # CopyHere roda em segundo plano: espera os arquivos pararem de crescer
    ultimo, estavel = -1, 0
    for _ in range(60 * 60 // INTERVALO):
        if extraido():
            tam = sum(f.stat().st_size for n in ESPERADOS for f in DATA_RAW.rglob(n))
            print(f"\r  extraído até agora: {tam / 1e9:.2f} GB   ", end="", flush=True)
            estavel = estavel + 1 if tam == ultimo else 0
            ultimo = tam
            if estavel >= 3:
                print()
                return
        time.sleep(INTERVALO)
    raise RuntimeError("a extração pelo Windows não terminou em 1 hora")


def extrair(zip_path: Path) -> None:
    metodos = [("Python", extrair_python), ("7-Zip", extrair_7zip), ("Windows", extrair_windows)]
    erros = []
    for nome, func in metodos:
        print(f"Extraindo com {nome} (uns 3 GB, pode levar alguns minutos)...")
        try:
            func(zip_path)
            if extraido():
                return
            erros.append(f"{nome}: terminou sem gerar os CSVs")
        except NotImplementedError:
            erros.append(f"{nome}: não suporta a compressão do zip (Deflate64)")
        except Exception as e:  # noqa: BLE001
            erros.append(f"{nome}: {e}")
        print("  " + erros[-1])
    sys.exit(
        "Não consegui extrair o zip.\n  " + "\n  ".join(erros) + "\n\n"
        "Extraia manualmente: clique com o botão direito no zip > Extrair tudo... e escolha\n"
        f"a pasta {DATA_RAW.resolve()}. Depois rode: python scripts/01_inspecionar.py"
    )


# ---------------------------------------------------------------- principal
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", type=Path, help="zip já baixado")
    ap.add_argument("--pasta", type=Path, help="pasta onde o navegador salva os downloads")
    args = ap.parse_args()

    DATA_RAW.mkdir(parents=True, exist_ok=True)
    if extraido():
        print("Os CSVs já estão extraídos em data/raw/. Nada a fazer.")
        return

    pastas = pastas_download(args.pasta)

    if args.zip:
        zip_path = args.zip
        if not zip_path.exists():
            sys.exit(f"Arquivo não encontrado: {zip_path}")
        if not zip_valido(zip_path):
            sys.exit(f"{zip_path} está incompleto ou não é o zip do ENEM 2025.")
    else:
        existentes = [z for z in zips_existentes(pastas) if zip_valido(z)]
        if existentes:
            zip_path = existentes[0]
            print(f"Zip encontrado: {zip_path}")
        else:
            antes = set(zips_existentes(pastas))
            print(f"Abrindo o download no navegador:\n  {URL}")
            if not webbrowser.open(URL):
                print("Não consegui abrir o navegador. Copie o link acima e cole no navegador.")
            zip_path = esperar_download(pastas, antes)
            if not zip_valido(zip_path):
                sys.exit(f"{zip_path} está incompleto. Apague e rode o script de novo.")

    extrair(zip_path)

    print("CSVs encontrados:")
    for c in sorted(DATA_RAW.rglob("*.csv")):
        print(f"  {c.relative_to(DATA_RAW)}  ({c.stat().st_size / 1e6:,.0f} MB)")
    print(f"\nPode apagar o zip ({zip_path}) se quiser liberar espaço.")
    print("Próximo passo: python scripts/01_inspecionar.py")


if __name__ == "__main__":
    main()
