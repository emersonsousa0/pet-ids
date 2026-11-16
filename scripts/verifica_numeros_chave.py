#!/usr/bin/env python3
"""Verificacao independente de numeros-chave do relatorio IDS 7.

Nao usa pandas e nao reaproveita funcoes de scripts/inspeciona_dataset.py.
Le os CSV com o modulo csv (streaming), classifica os blocos e recalcula:
  - tamanho dos blocos A, B e C;
  - % de Label=1 por bloco;
  - dur == Ltime - Stime (linhas ISO-8601);
  - Sload == sbytes / dur (linhas com dur > 0);
  - duplicatas exatas;
  - IPs da faixa 10.0.0.0/8 (para conferir a exclusao da rede Bridge).

Uso:
    python3 scripts/verifica_numeros_chave.py
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "Dataset_completo.csv"
SUMMARY = ROOT / "Dataset_resumido.csv"

NUMERIC_PROTO = re.compile(r"^[0-9]+(?:[.,][0-9]+)*$")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")


def is_number(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False


def iso_to_epoch(text: str) -> float | None:
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def main() -> None:
    counts = Counter()
    label_by_block = {"A": Counter(), "B": Counter(), "C": Counter()}
    iso_pairs = 0
    iso_equal = 0
    load_pairs = 0
    load_equal = 0
    seen = set()
    duplicates = 0
    ip10 = Counter()
    ip10_cols = Counter()
    presence = {}
    sentinels = {"0", "0.0", ""}

    with FULL.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            proto = row["proto"]
            named = not bool(NUMERIC_PROTO.match(proto))
            stime_zero = row["Stime"] == "0"
            if named and stime_zero:
                block = "A"
            elif named:
                block = "B"
            else:
                block = "C"
            counts[block] += 1
            label_by_block[block][row["Label"]] += 1

            # presenca por bloco: Label conta sempre (0 e 1 sao valores reais);
            # nas demais colunas, 0/0.0/vazio sao tratados como sentinela.
            if not presence:
                presence = {c: {"A": 0, "B": 0, "C": 0} for c in row}
            for col, val in row.items():
                if col == "Label" or val not in sentinels:
                    presence[col][block] += 1

            # duplicata exata = tupla da linha inteira
            key = tuple(row.values())
            if key in seen:
                duplicates += 1
            else:
                seen.add(key)

            # dur == Ltime - Stime, somente quando ambos sao ISO-8601
            if ISO.match(row["Stime"]) and ISO.match(row["Ltime"]):
                start = iso_to_epoch(row["Stime"])
                end = iso_to_epoch(row["Ltime"])
                dur = float(row["dur"])
                if start is not None and end is not None:
                    iso_pairs += 1
                    if abs((end - start) - dur) <= 1e-6:
                        iso_equal += 1

            # Sload == sbytes / dur, somente com dur > 0
            dur = float(row["dur"])
            if dur > 0:
                sbytes = float(row["sbytes"])
                sload = float(row["Sload"])
                load_pairs += 1
                if abs(sload - sbytes / dur) <= 1e-9 * max(1.0, abs(sload)):
                    load_equal += 1

            for col in ("srcip", "dstip"):
                for ip in row[col].split(","):
                    ip = ip.strip()
                    if ip.startswith("10."):
                        ip10[ip] += 1
                        ip10_cols[col] += 1

    total = sum(counts.values())
    print("=" * 72)
    print("VERIFICACAO INDEPENDENTE (csv puro, sem pandas)")
    print("=" * 72)
    print(f"Linhas lidas: {total}")
    print(f"Blocos: A={counts['A']}  B={counts['B']}  C={counts['C']}")
    for b in ("A", "B", "C"):
        n = sum(label_by_block[b].values())
        pct = 100.0 * label_by_block[b]["1"] / n if n else 0.0
        print(f"  Bloco {b}: Label=1 {label_by_block[b]['1']}/{n} = {pct:.4f}%")
    print(f"dur == Ltime - Stime: {iso_equal}/{iso_pairs} "
          f"({100.0 * iso_equal / iso_pairs:.4f}%)")
    print(f"Sload == sbytes/dur:  {load_equal}/{load_pairs} "
          f"({100.0 * load_equal / load_pairs:.4f}%)")
    print(f"Duplicatas exatas:    {duplicates}")
    print(f"IPs 10.0.0.0/8:       {sum(ip10.values())} ocorrencias "
          f"(srcip={ip10_cols['srcip']}, dstip={ip10_cols['dstip']})")
    for ip, n in ip10.most_common(10):
        print(f"  {ip}: {n}")

    print("\nPresenca nao-sentinela por bloco (Label conta sempre):")
    for col in presence:
        a, b, c = presence[col]["A"], presence[col]["B"], presence[col]["C"]
        print(f"  {col:15s} A={a:6d} B={b:6d} C={c:6d}")

    # Confere os totais do resumido
    res_total = 0
    res_label = Counter()
    with SUMMARY.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            res_total += 1
            res_label[row["Label"]] += 1
    print(f"\nResumido: {res_total} linhas; Label=1 {res_label['1']} "
          f"({100.0 * res_label['1'] / res_total:.4f}%)")

    out = {
        "linhas_completo": total,
        "blocos": dict(counts),
        "label1_por_bloco": {
            b: {
                "n": sum(label_by_block[b].values()),
                "label1": label_by_block[b]["1"],
                "pct": round(100.0 * label_by_block[b]["1"] / sum(label_by_block[b].values()), 4),
            }
            for b in ("A", "B", "C")
        },
        "dur_igual_ltime_menos_stime": {"n": iso_pairs, "iguais": iso_equal},
        "sload_igual_sbytes_por_dur": {"n": load_pairs, "iguais": load_equal},
        "duplicatas_exatas": duplicates,
        "ips_10_0_0_0_8": {
            "ocorrencias": sum(ip10.values()),
            "por_coluna": dict(ip10_cols),
            "top": dict(ip10.most_common(10)),
        },
        "resumido": {
            "linhas": res_total,
            "label1": res_label["1"],
            "label1_pct": round(100.0 * res_label["1"] / res_total, 4),
            "label0": res_label["0"],
        },
        "presenca_nao_sentinela_por_bloco": presence,
    }
    (ROOT / "docs/verificacao_numeros_chave.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("\nJSON: docs/verificacao_numeros_chave.json")


if __name__ == "__main__":
    main()
