#!/usr/bin/env python3
"""Compara as linhas A+B do Dataset_completo com o Dataset_resumido.

Hipotese a testar: o resumido e o completo sem as linhas do bloco C (proto numerico),
na mesma ordem. A comparacao e feita em TODAS as colunas comuns, linha a linha, e cada
celula cai em uma de quatro categorias:

  igual                 texto identico
  numerico_equivalente  mesmo numero com formatacao diferente (ex.: "80" vs "80.0")
  vazio_vs_zero         um lado vazio e o outro 0 / 0.0 (politica de nulos diferente)
  diferente             qualquer outra divergencia

Uso:
  python3 compara_resumido_ab.py --completo Dataset_completo.csv --resumido Dataset_resumido.csv
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict

VAZIO_OU_ZERO = {"", "0", "0.0"}


def proto_numerico(valor: str) -> bool:
    """True se proto nao tem letras (assinatura do bloco C).

    Aceita numeros puros ("6", "6.0") e valores compostos sem letras ("6,17"), que
    float() rejeitaria e deixaria cair por engano no bloco A+B.
    """
    v = valor.strip()
    return bool(v) and not any(ch.isalpha() for ch in v)


def numero_puro(valor: str) -> bool:
    try:
        float(valor)
        return True
    except ValueError:
        return False


def classifica(c: str, r: str) -> str:
    if c == r:
        return "igual"
    if c.strip() in VAZIO_OU_ZERO and r.strip() in VAZIO_OU_ZERO:
        return "vazio_vs_zero"
    try:
        if float(c) == float(r):
            return "numerico_equivalente"
    except ValueError:
        pass
    return "diferente"


def celula(linha, idx):
    return linha[idx] if idx < len(linha) else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--completo", default="Dataset_completo.csv")
    ap.add_argument("--resumido", default="Dataset_resumido.csv")
    ap.add_argument("--amostras", type=int, default=3, help="exemplos de divergencia por coluna")
    ap.add_argument("--json", default=None, help="caminho opcional para salvar o resultado")
    a = ap.parse_args()

    csv.field_size_limit(sys.maxsize)
    por_coluna = defaultdict(Counter)
    amostras = defaultdict(list)
    n_c = n_ab = n_resumido = n_comparadas = 0
    sobra_completo = 0
    c_composto = []

    with open(a.completo, newline="", encoding="utf-8") as fc, \
         open(a.resumido, newline="", encoding="utf-8") as fr:
        rc, rr = csv.reader(fc), csv.reader(fr)
        hc, hr = next(rc), next(rr)
        comuns = [c for c in hr if c in hc]
        so_completo = [c for c in hc if c not in hr]
        so_resumido = [c for c in hr if c not in hc]
        ic = {c: hc.index(c) for c in comuns}
        ir = {c: hr.index(c) for c in comuns}
        ordem_igual = [c for c in hc if c in hr] == [c for c in hr if c in hc]
        if "proto" not in ic:
            print("ERRO: coluna 'proto' nao existe nas duas bases; nao da para separar o bloco C.")
            return 1

        for linha_c in rc:
            n_c += 1
            if proto_numerico(celula(linha_c, ic["proto"])):
                if not numero_puro(celula(linha_c, ic["proto"])):
                    c_composto.append(celula(linha_c, ic["proto"]))
                continue  # bloco C: fora do resumido
            n_ab += 1
            linha_r = next(rr, None)
            if linha_r is None:
                sobra_completo += 1
                continue
            n_resumido += 1
            n_comparadas += 1
            for col in comuns:
                vc, vr = celula(linha_c, ic[col]), celula(linha_r, ir[col])
                cat = classifica(vc, vr)
                por_coluna[col][cat] += 1
                if cat == "diferente" and len(amostras[col]) < a.amostras:
                    amostras[col].append({"linha_ab": n_ab, "completo": vc, "resumido": vr})
        sobra_resumido = sum(1 for _ in rr)
        n_resumido += sobra_resumido

    print(f"Linhas no completo:                 {n_c}")
    print(f"  bloco C (proto numerico):         {n_c - n_ab}")
    print(f"  (dentro do C, proto nao e numero puro: {len(c_composto)} {c_composto[:5]})")
    print(f"  A+B (proto nomeado):              {n_ab}")
    print(f"Linhas no resumido:                 {n_resumido}")
    print(f"Linhas A+B sem par no resumido:     {sobra_completo}")
    print(f"Linhas do resumido sem par no A+B:  {sobra_resumido}")
    print(f"Colunas comuns comparadas:          {len(comuns)}")
    print(f"Mesma ordem das colunas comuns:     {ordem_igual}")
    print(f"So no completo: {so_completo} | So no resumido: {so_resumido}\n")

    cab = f"{'coluna':<18}{'igual':>9}{'num_eq':>9}{'vazio~0':>9}{'difer.':>9}"
    print(cab)
    print("-" * len(cab))
    total_dif = 0
    for col in comuns:
        c = por_coluna[col]
        total_dif += c["diferente"]
        print(f"{col:<18}{c['igual']:>9}{c['numerico_equivalente']:>9}"
              f"{c['vazio_vs_zero']:>9}{c['diferente']:>9}")
    print()
    colunas_com_dif = [c for c in comuns if por_coluna[c]["diferente"]]
    if colunas_com_dif:
        print("Exemplos de divergencia real:")
        for col in colunas_com_dif:
            for ex in amostras[col]:
                print(f"  {col} (linha A+B {ex['linha_ab']}): completo={ex['completo']!r} resumido={ex['resumido']!r}")
    veredito = (n_ab == n_resumido and sobra_completo == 0 and sobra_resumido == 0 and total_dif == 0)
    print("\nVeredito: " + (
        "A+B corresponde ao resumido em todas as colunas comuns (diferencas so de formato ou de vazio vs 0)."
        if veredito else
        "NAO bate por completo: ver contagens e divergencias acima."))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({
                "linhas": {"completo": n_c, "bloco_c": n_c - n_ab, "ab": n_ab, "resumido": n_resumido},
                "sem_par": {"ab": sobra_completo, "resumido": sobra_resumido},
                "colunas_comuns": comuns, "so_completo": so_completo, "so_resumido": so_resumido,
                "mesma_ordem": ordem_igual,
                "por_coluna": {c: dict(por_coluna[c]) for c in comuns},
                "amostras_divergencia": amostras,
            }, fh, ensure_ascii=False, indent=2)
        print(f"Resultado salvo em {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
