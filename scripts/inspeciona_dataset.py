#!/usr/bin/env python3
"""Inspeciona os CSVs do dataset PET/IDS e registra os fatos medidos.

Uso:
    python3 scripts/inspeciona_dataset.py
    python3 scripts/inspeciona_dataset.py --json docs/inspecao_dataset.json

O script NAO altera os CSVs: le tudo como texto (dtype=str) para nao perder
sentinels nem formatos mistos (ex.: `0`, `0.0`, `True`, `2025-08-20 ...`).

Saidas:
    - resumo legivel no stdout;
    - JSON completo (opcional, com --json) com todas as metricas.

Requisitos: pandas, numpy.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
FULL = REPO_ROOT / "Dataset_completo.csv"
SUMMARY = REPO_ROOT / "Dataset_resumido.csv"

# Colunas que o contrato assume numericas; usadas para medir texto indevido.
EXPECTED_NUMERIC = [
    "sport", "dsport", "dur", "sbytes", "dbytes", "sttl", "Sload", "Dload",
    "Spkts", "Dpkts", "swin", "stcpb", "dtcpb", "smeansz", "dmeansz",
    "trans_depth", "res_bdy_len", "Stime", "Ltime", "synack", "ackdat",
    "is_sm_ips_ports", "ct_state_ttl", "Label",
]
# Colunas de fluxo usadas no bloco "linhas totalmente zeradas".
FLOW_FEATURES = [
    "dur", "sbytes", "dbytes", "Sload", "Dload", "Spkts", "Dpkts",
    "smeansz", "dmeansz",
]
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}")
EPOCH_RE = re.compile(r"^\d{10}(\.\d+)?$")
NUM_RE = re.compile(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$")


def load_csv(path: Path) -> pd.DataFrame:
    """Le o CSV inteiro como texto, preservando vazios e sentinelas."""
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        low_memory=False,
    )


def infer_dtype(s: pd.Series, expected_numeric: bool = False) -> tuple[str, dict]:
    """Infere o tipo *real* observado (nao o tipo que o pandas adivinha)."""
    non_blank = s[s != ""]
    info: dict = {"fracao_numerica": None, "formato": None}
    if non_blank.empty:
        return "vazia", info

    num = pd.to_numeric(non_blank, errors="coerce")
    frac_num = float(num.notna().mean())
    info["fracao_numerica"] = round(frac_num, 6)

    is_iso = non_blank.str.match(ISO_RE)
    is_epoch = non_blank.str.fullmatch(EPOCH_RE)
    is_bool = non_blank.isin(["True", "False", "true", "false"])

    if is_bool.all():
        info["formato"] = "bool_texto"
        return "bool (texto)", info
    if frac_num == 1.0:
        if np.allclose(num.to_numpy(dtype=float), np.round(num.to_numpy(dtype=float))):
            info["formato"] = "inteiro_texto"
            return "int64 (texto)", info
        info["formato"] = "decimal_texto"
        return "float64 (texto)", info
    if is_iso.mean() > 0.99:
        info["formato"] = "iso8601"
        return "string ISO-8601", info
    if is_epoch.mean() > 0.99:
        info["formato"] = "epoch"
        return "string epoch", info
    if frac_num == 0.0:
        info["formato"] = "texto"
        return "string", info

    # Tipo misto: descreve as familias presentes.
    parts = []
    if frac_num > 0:
        parts.append(f"{frac_num:.1%} numerico")
    if is_bool.any():
        parts.append(f"{is_bool.mean():.1%} bool")
    if is_iso.any():
        parts.append(f"{is_iso.mean():.1%} ISO-8601")
    rest = non_blank[~non_blank.map(lambda x: bool(NUM_RE.match(x)))]
    if not rest.empty:
        parts.append(f"{len(rest)} texto (ex.: {rest.iloc[0]!r})")
    info["formato"] = "misto"

    # Categorica com sentinela '0' e normal; nao e "erro de tipo".
    if (
        not expected_numeric
        and (num.fillna(0) == 0).all()
        and not rest.empty
        and rest.nunique() <= 50
    ):
        info["formato"] = "categorica_com_sentinela"
        return "string (categorica, sentinela '0')", info

    return "misto (object): " + ", ".join(parts), info


def column_stats(s: pd.Series, *, expected_numeric: bool = False, top_n: int = 5) -> dict:
    """Metricas de uma coluna."""
    n = len(s)
    blank = int((s == "").sum())
    non_blank = s[s != ""]
    num = pd.to_numeric(non_blank, errors="coerce")
    is_inf = np.isinf(num.to_numpy(dtype=float, na_value=np.nan))
    n_text = int((num.isna()).sum())
    zeros = int((num == 0).sum())
    dtype, dtype_info = infer_dtype(s, expected_numeric)

    numeric = None
    if num.notna().any():
        valid = num.dropna()
        numeric = {
            "n_parseados": int(valid.size),
            "n_texto": n_text,
            "n_inf": int(is_inf.sum()),
            "n_zero": zeros,
            "pct_linhas_zero": round(100.0 * zeros / n, 3),
            "min": float(valid.min()),
            "p01": float(valid.quantile(0.01)),
            "p50": float(valid.quantile(0.50)),
            "p99": float(valid.quantile(0.99)),
            "max": float(valid.max()),
        }

    counts = s.value_counts(dropna=False)
    out = {
        "dtype_inferido": dtype,
        "dtype_evidencia": dtype_info,
        "n": n,
        "n_nulos": blank,
        "pct_nulos": round(100.0 * blank / n, 3),
        "n_unicos": int(s.nunique()),
        "literal_0": int((s == "0").sum()),
        "top5": [[str(k), int(v)] for k, v in counts.head(top_n).items()],
        "numerico": numeric,
    }
    return out


def ts_kind(x: str) -> str:
    if x == "":
        return "vazio"
    if x == "0":
        return "sentinela_0"
    if ISO_RE.match(x):
        return "iso8601"
    if EPOCH_RE.match(x):
        return "epoch"
    return "outro"


def to_epoch(s: pd.Series) -> pd.Series:
    """Converte ISO-8601 e epoch (segundos) para epoch; demais viram NaN."""
    iso = pd.to_datetime(s.where(s.str.match(ISO_RE)), errors="coerce", utc=True)
    epoch = pd.to_numeric(s.where(s.str.fullmatch(EPOCH_RE)), errors="coerce")
    return iso.map(lambda t: t.timestamp() if pd.notna(t) else np.nan).fillna(epoch)


def build_blocks(df: pd.DataFrame) -> pd.DataFrame:
    """Classifica as linhas nos blocos de origem aparentes.

    A classificacao usa apenas fatos observados:
      - proto com nome (TCP/UDP/...) vs codigo numerico (6/17/1...);
      - Stime sentinela '0' vs preenchido.
    """
    proto_named = ~df["proto"].str.fullmatch(r"[\d.,]+")
    stime_missing = df["Stime"] == "0"
    block = np.select(
        [proto_named & stime_missing, proto_named & ~stime_missing, ~proto_named],
        ["A: proto nome + Stime=0", "B: proto nome + Stime preenchido", "C: proto numerico"],
        default="outro",
    )
    return pd.Series(block, index=df.index, name="bloco")


def block_profile(df: pd.DataFrame, blocks: pd.Series) -> list[dict]:
    out = []
    for name, b in df.groupby(blocks, sort=True):
        row = {
            "bloco": name,
            "n_linhas": len(b),
            "pct_do_total": round(100.0 * len(b) / len(df), 3),
            "label_1": int((b["Label"] == "1").sum()),
            "pct_label_1": round(100.0 * (b["Label"] == "1").mean(), 3),
            "pct_dur_0": round(100.0 * b["dur"].isin(["0", "0.0"]).mean(), 3),
            "pct_state_0": round(100.0 * (b["state"] == "0").mean(), 3),
            "pct_sbytes_0": round(100.0 * b["sbytes"].isin(["0", "0.0"]).mean(), 3),
            "pct_stime_sentinela": round(
                100.0 * (b["Stime"] == "0").mean(), 3
            ),
            "n_trans_depth_texto": int(
                (~b["trans_depth"].str.fullmatch(r"-?\d+(\.\d+)?")).sum()
            ),
            "n_5tuplas_unicas": int(
                b[["srcip", "sport", "dstip", "dsport", "proto"]]
                .drop_duplicates()
                .shape[0]
            ),
            "spkts_top3": b["Spkts"].value_counts().head(3).to_dict(),
            "dpkts_top3": b["Dpkts"].value_counts().head(3).to_dict(),
        }
        for col in ["sttl", "swin", "stcpb", "dtcpb"]:
            if col in b:
                row[f"{col}_pct_zero"] = round(
                    100.0 * b[col].isin(["0", "0.0"]).mean(), 3
                )
        out.append(row)
    return out


def formula_checks(df: pd.DataFrame) -> dict:
    """Testa relacoes exatas entre colunas (evidencia de unidade/derivacao)."""
    num = {c: pd.to_numeric(df[c], errors="coerce") for c in
           ["dur", "sbytes", "dbytes", "Spkts", "Dpkts", "Sload", "Dload",
            "smeansz", "dmeansz"]}

    def pct(mask, cond):
        n = int(mask.sum())
        return {
            "n": n,
            "pct": round(100.0 * float(cond[mask].mean()), 4) if n else None,
        }

    dur_pos = num["dur"] > 0
    spkts_pos = num["Spkts"] > 0
    dpkts_pos = num["Dpkts"] > 0

    # dur == Ltime - Stime, quando ambos sao datas ISO-8601
    iso = df["Stime"].str.match(ISO_RE) & df["Ltime"].str.match(ISO_RE)
    diff = (
        pd.to_datetime(df.loc[iso, "Ltime"], utc=True)
        - pd.to_datetime(df.loc[iso, "Stime"], utc=True)
    ).dt.total_seconds()
    diff_ok = pd.Series(False, index=df.index)
    diff_ok.loc[iso] = np.isclose(diff, num["dur"][iso], rtol=1e-6)

    return {
        "Sload == sbytes / dur": pct(
            dur_pos, np.isclose(num["Sload"], num["sbytes"] / num["dur"], rtol=1e-9)
        ),
        "Sload == sbytes * 8 / dur": pct(
            dur_pos, np.isclose(num["Sload"], num["sbytes"] * 8 / num["dur"], rtol=1e-9)
        ),
        "Dload == dbytes / dur": pct(
            dur_pos, np.isclose(num["Dload"], num["dbytes"] / num["dur"], rtol=1e-9)
        ),
        "Dload == dbytes * 8 / dur": pct(
            dur_pos, np.isclose(num["Dload"], num["dbytes"] * 8 / num["dur"], rtol=1e-9)
        ),
        "smeansz == sbytes / Spkts": pct(
            spkts_pos, np.isclose(num["smeansz"], num["sbytes"] / num["Spkts"], rtol=1e-9)
        ),
        "dmeansz == dbytes / Dpkts": pct(
            dpkts_pos, np.isclose(num["dmeansz"], num["dbytes"] / num["Dpkts"], rtol=1e-9)
        ),
        "dur == Ltime - Stime (linhas ISO)": pct(iso, diff_ok),
    }


def duplicates_info(df: pd.DataFrame) -> dict:
    exact = int(df.duplicated(keep="first").sum())
    sem_http = int(df.drop(columns=["trans_depth", "res_bdy_len"]).duplicated(keep="first").sum())
    return {
        "linhas_duplicadas_exatas": exact,
        "pct_duplicadas_exatas": round(100.0 * exact / len(df), 3),
        "linhas_duplicadas_ignorando_trans_depth_res_bdy_len": sem_http,
        "nota": (
            "duplicata exata = linha inteira identica; a segunda contagem remove as "
            "duas colunas de HTTP, que carregam metodo/URL"
        ),
    }


def examples_texto_em_numerico(df: pd.DataFrame, cols: list[str], k: int = 5) -> list[dict]:
    mask = pd.Series(False, index=df.index)
    for c in cols:
        if c in df:
            mask |= ~df[c].str.fullmatch(r"-?\d+(\.\d+)?([eE][-+]?\d+)?") & (df[c] != "")
    cols_show = [c for c in ["srcip", "sport", "dstip", "dsport", "proto", "state",
                             "service", "trans_depth", "res_bdy_len", "Stime", "Ltime",
                             "Label"] if c in df]
    return df.loc[mask, cols_show].head(k).to_dict(orient="records")


def quality(df: pd.DataFrame, blocks: pd.Series) -> dict:
    q: dict = {}

    # 1. Texto em colunas que deveriam ser numericas.
    por_coluna = {}
    for c in EXPECTED_NUMERIC:
        if c not in df:
            continue
        bad = (~df[c].str.fullmatch(r"-?\d+(\.\d+)?([eE][-+]?\d+)?")) & (df[c] != "")
        if bad.any():
            por_coluna[c] = {
                "n": int(bad.sum()),
                "pct": round(100.0 * bad.mean(), 3),
                "exemplos": df.loc[bad, c].value_counts().head(5).to_dict(),
            }
    q["texto_em_coluna_numerica"] = por_coluna

    # 2. Deslocamento / reuso de colunas HTTP.
    shifted = ~df["trans_depth"].str.fullmatch(r"-?\d+(\.\d+)?")
    q["linhas_com_metodo_http_em_trans_depth"] = int(shifted.sum())
    q["pct_linhas_com_metodo_http_em_trans_depth"] = round(100.0 * shifted.mean(), 3)
    q["metodos_http_encontrados"] = (
        df.loc[shifted, "trans_depth"].value_counts().to_dict()
    )
    uris = df.loc[shifted, "res_bdy_len"]
    q["linhas_com_uri_em_res_bdy_len"] = int((~uris.str.fullmatch(r"-?\d+(\.\d+)?")).sum())
    q["exemplos_http_deslocado"] = examples_texto_em_numerico(
        df, ["trans_depth", "res_bdy_len"], 5
    )
    q["label_nas_linhas_http_deslocadas"] = (
        df.loc[shifted, "Label"].value_counts().to_dict()
    )

    # 3. Timestamps.
    q["stime_formatos"] = df["Stime"].map(ts_kind).value_counts().to_dict()
    q["ltime_formatos"] = df["Ltime"].map(ts_kind).value_counts().to_dict()
    st = to_epoch(df["Stime"])
    lt = to_epoch(df["Ltime"])
    both = st.notna() & lt.notna() & (st > 0) & (lt > 0)
    q["linhas_timestamp_comparavel"] = int(both.sum())
    q["linhas_ltime_igual_stime"] = int((lt[both] == st[both]).sum())
    q["linhas_ltime_menor_que_stime"] = int((lt[both] < st[both]).sum())
    q["stime_epoch_min"] = None if st.dropna().empty else float(st.min())
    q["stime_epoch_max"] = None if st.dropna().empty else float(st.max())

    # 4. Divisao por zero.
    dur = pd.to_numeric(df["dur"], errors="coerce")
    sload = pd.to_numeric(df["Sload"], errors="coerce")
    sbytes = pd.to_numeric(df["sbytes"], errors="coerce")
    z = (dur == 0)
    q["linhas_dur_zero"] = int(z.sum())
    q["linhas_dur_zero_e_sload_nao_zero"] = int((z & (sload != 0)).sum())
    q["linhas_dur_zero_sload_igual_sbytes"] = int(
        (z & (sload != 0) & np.isclose(sload, sbytes)).sum()
    )
    q["exemplos_dur_zero_sload_nao_zero"] = (
        df.loc[z & (sload != 0),
               ["srcip", "dstip", "proto", "dur", "sbytes", "Sload", "Dload", "Label"]]
        .head(5)
        .to_dict(orient="records")
    )
    q["n_inf_sload"] = int(np.isinf(sload).sum())
    q["n_inf_dload"] = int(np.isinf(pd.to_numeric(df["Dload"], errors="coerce")).sum())

    # 5. Multiplos valores no mesmo campo (agregacao indevida).
    multi = pd.Series(False, index=df.index)
    for c in ["srcip", "dstip", "sport", "dsport", "proto", "sttl"]:
        if c in df:
            multi |= df[c].str.contains(",", regex=False)
    q["linhas_com_multiplos_valores_no_mesmo_campo"] = int(multi.sum())
    q["exemplos_multiplos_valores"] = (
        df.loc[multi, [c for c in ["srcip", "dstip", "proto", "sttl", "Label"] if c in df]]
        .head(5)
        .to_dict(orient="records")
    )

    # 6. Linhas sem nenhuma feature de fluxo.
    zfeat = (df[FLOW_FEATURES].apply(pd.to_numeric, errors="coerce") == 0).sum(axis=1)
    q["linhas_com_todas_as_features_de_fluxo_zero"] = int((zfeat == len(FLOW_FEATURES)).sum())
    q["pct_linhas_com_todas_as_features_de_fluxo_zero"] = round(
        100.0 * (zfeat == len(FLOW_FEATURES)).mean(), 3
    )

    # 7. Colunas constantes.
    q["colunas_constantes"] = {
        c: str(df[c].iloc[0]) for c in df.columns if df[c].nunique() == 1
    }

    # 8. Codificacao de proto.
    q["proto_valores"] = df["proto"].value_counts().to_dict()
    q["proto_numerico_linhas"] = int(df["proto"].str.fullmatch(r"[\d.,]+").sum())
    q["proto_nomeado_linhas"] = int((~df["proto"].str.fullmatch(r"[\d.,]+")).sum())

    # 9. sttl/swin/stcpb/dtcpb (o resumido nao tem algumas destas colunas).
    for c in ["sttl", "swin", "stcpb", "dtcpb"]:
        if c not in df:
            continue
        vc = df[c].value_counts()
        q[f"{c}_top"] = vc.head(8).to_dict()
        q[f"{c}_pct_zero"] = round(100.0 * (df[c].isin(["0", "0.0"])).mean(), 3)
        q[f"{c}_n_unicos"] = int(df[c].nunique())
    q["stcpb_igual_dtcpb_pct"] = round(100.0 * (df["stcpb"] == df["dtcpb"]).mean(), 3) \
        if "stcpb" in df and "dtcpb" in df else None

    # 10. ct_state_ttl nao e contagem: carrega nomes de estado.
    q["ct_state_ttl_valores"] = df["ct_state_ttl"].value_counts().to_dict()
    q["ct_state_ttl_x_state"] = (
        pd.crosstab(df["state"], df["ct_state_ttl"]).to_dict()
    )

    # 11. Distribuicao por bloco.
    q["blocos"] = block_profile(df, blocks)

    # 11b. Relacoes exatas entre colunas.
    q["formulas"] = formula_checks(df)

    # 12. Duplicatas.
    q["duplicatas"] = duplicates_info(df)

    return q


def compare(full: pd.DataFrame, res: pd.DataFrame) -> dict:
    """Compara dataset completo e resumido."""
    cols_full, cols_res = list(full.columns), list(res.columns)

    # Subconjunto por proto nomeado?
    named = full[~full["proto"].str.fullmatch(r"[\d.,]+")]
    same_n = len(named) == len(res)

    id_cols = ["srcip", "dstip", "proto"]
    identity = {
        c: bool((named[c].reset_index(drop=True) == res[c].reset_index(drop=True)).all())
        for c in id_cols
    }
    # portas: o resumido transforma '0.0' em vazio
    port_match = {}
    for c in ["sport", "dsport"]:
        f = named[c].reset_index(drop=True)
        r = res[c].reset_index(drop=True)
        port_match[c] = bool(
            ((f == r) | ((r == "") & f.isin(["0", "0.0"]))).all()
        )

    # Regra de blanks: resumido troca sentinela '0' por vazio?
    blank_rule = {}
    for c in cols_res:
        if c not in named:
            continue
        f = named[c].reset_index(drop=True)
        r = res[c].reset_index(drop=True)
        blank_rule[c] = {
            "linhas_vazias_no_resumido": int((r == "").sum()),
            "vazio_onde_completo_tem_sentinela_0": int(((r == "") & (f.isin(["0", "0.0", "False"]))).sum()),
            "valores_iguais": int((f == r).sum()),
            "outras_diferencas": int(((f != r) & (r != "")).sum()),
        }

    return {
        "colunas_completo": cols_full,
        "colunas_resumido": cols_res,
        "colunas_so_no_completo": [c for c in cols_full if c not in cols_res],
        "colunas_so_no_resumido": [c for c in cols_res if c not in cols_full],
        "mesma_ordem_nas_colunas_comuns": cols_res == [c for c in cols_full if c in cols_res],
        "linhas_completo": len(full),
        "linhas_resumido": len(res),
        "pct_do_completo": round(100.0 * len(res) / len(full), 3),
        "resumido_e_subconjunto_do_completo": same_n and all(identity.values()),
        "identidade_linha_a_linha": identity,
        "portas_compativeis": port_match,
        "rotulo_completo": full["Label"].value_counts().to_dict(),
        "rotulo_resumido": res["Label"].value_counts().to_dict(),
        "regra_de_vazio_do_resumido": blank_rule,
        "dtypes_completo": {
            c: infer_dtype(full[c], c in EXPECTED_NUMERIC or c == "proto")[0]
            for c in cols_full
        },
        "dtypes_resumido": {
            c: infer_dtype(res[c], c in EXPECTED_NUMERIC or c == "proto")[0]
            for c in cols_res
        },
    }


def analyze(path: Path, name: str) -> dict:
    df = load_csv(path)
    blocks = build_blocks(df)
    stats = {
        c: column_stats(df[c], expected_numeric=(c in EXPECTED_NUMERIC or c == "proto"))
        for c in df.columns
    }
    return {
        "arquivo": name,
        "bytes": path.stat().st_size,
        "shape": {"linhas": int(df.shape[0]), "colunas": int(df.shape[1])},
        "colunas": list(df.columns),
        "dtypes": {
            c: infer_dtype(df[c], c in EXPECTED_NUMERIC or c == "proto")[0]
            for c in df.columns
        },
        "estatisticas_por_coluna": stats,
        "distribuicao_label": df["Label"].value_counts().to_dict(),
        "distribuicao_service": df["service"].value_counts().to_dict(),
        "distribuicao_state": df["state"].value_counts().to_dict(),
        "qualidade": quality(df, blocks),
    }


def print_resumo(full_info: dict, res_info: dict, comp: dict) -> None:
    def line() -> None:
        print("-" * 78)

    print("=" * 78)
    print("INSPECAO DO DATASET (scripts/inspeciona_dataset.py)")
    print("=" * 78)
    for info in (full_info, res_info):
        print(f"\n{info['arquivo']}: {info['shape']['linhas']} linhas x "
              f"{info['shape']['colunas']} colunas, {info['bytes']/1e6:.1f} MB")
        print("Label:", info["distribuicao_label"])
        print("state:", info["distribuicao_state"])
        print("service:", info["distribuicao_service"])

    print("\nCOLUNAS COM TIPO MISTO OU TEXTO INDEVIDO (completo):")
    for c, st in full_info["estatisticas_por_coluna"].items():
        if (c in EXPECTED_NUMERIC or c == "proto") and "misto" in st["dtype_inferido"]:
            print(f"  {c:16s} {st['dtype_inferido']}")

    q = full_info["qualidade"]
    print("\nPROBLEMAS DE QUALIDADE (completo):")
    print(f"  linhas com metodo HTTP em trans_depth: {q['linhas_com_metodo_http_em_trans_depth']}")
    print(f"  linhas com URI em res_bdy_len:         {q['linhas_com_uri_em_res_bdy_len']}")
    print(f"  linhas com dur=0:                      {q['linhas_dur_zero']}")
    print(f"  ... e Sload!=0 (deveria ser 0/inf):    {q['linhas_dur_zero_e_sload_nao_zero']}")
    print(f"  linhas com varios valores no campo:    {q['linhas_com_multiplos_valores_no_mesmo_campo']}")
    print(f"  linhas com todas as features zero:     {q['linhas_com_todas_as_features_de_fluxo_zero']}")
    print(f"  Stime formatos: {q['stime_formatos']}")
    print(f"  Ltime == Stime (onde comparavel):      {q['linhas_ltime_igual_stime']}/{q['linhas_timestamp_comparavel']}")
    print(f"  duplicatas exatas:                     {q['duplicatas']['linhas_duplicadas_exatas']}")
    print(f"  colunas constantes:                    {q['colunas_constantes']}")
    print("\nBLOCOS APARENTES (completo):")
    for b in q["blocos"]:
        print(f"  {b['bloco']}: n={b['n_linhas']:6d} label1={b['pct_label_1']:6.2f}% "
              f"dur0={b['pct_dur_0']:6.2f}% state0={b['pct_state_0']:6.2f}% "
              f"td_texto={b['n_trans_depth_texto']} 5tuplas={b['n_5tuplas_unicas']}")

    print("\nRELACOES EXATAS ENTRE COLUNAS (completo):")
    for k, v in q["formulas"].items():
        print(f"  {k}: {v['pct']}% de {v['n']} linhas")

    print("\nCOMPARACAO COMPLETO x RESUMIDO:")
    print(f"  colunas so no completo: {comp['colunas_so_no_completo']}")
    print(f"  resumido e subconjunto do completo: {comp['resumido_e_subconjunto_do_completo']}")
    print(f"  linhas: {comp['linhas_completo']} -> {comp['linhas_resumido']} "
          f"({comp['pct_do_completo']}%)")
    print(f"  rotulo completo: {comp['rotulo_completo']}")
    print(f"  rotulo resumido: {comp['rotulo_resumido']}")
    print("\nDtypes divergentes entre completo e resumido:")
    for c in comp["colunas_resumido"]:
        d1 = comp["dtypes_completo"][c]
        d2 = comp["dtypes_resumido"][c]
        if d1 != d2:
            print(f"  {c:16s} completo={d1} | resumido={d2}")
    line()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=None,
                        help="grava o resultado completo em JSON")
    args = parser.parse_args()

    if not FULL.exists() or not SUMMARY.exists():
        raise SystemExit(f"CSVs nao encontrados em {REPO_ROOT}")

    full = load_csv(FULL)
    res = load_csv(SUMMARY)
    full_info = analyze(FULL, FULL.name)
    res_info = analyze(SUMMARY, SUMMARY.name)
    comp = compare(full, res)
    out = {"completo": full_info, "resumido": res_info, "comparacao": comp}

    print_resumo(full_info, res_info, comp)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                out,
                ensure_ascii=False,
                indent=2,
                default=lambda o: o.item() if hasattr(o, "item") else str(o),
            )
            + "\n"
        )
        print(f"JSON gravado em {args.json}")


if __name__ == "__main__":
    main()
