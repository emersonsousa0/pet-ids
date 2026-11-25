from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


COLUNAS_FLUXO = ["srcip", "sport", "dstip", "dsport", "proto"]

FEATURES = [
    "proto", "state", "dur", "sbytes", "dbytes", "sttl",
    "service", "Sload", "Dload", "Spkts", "Dpkts", "swin",
    "smeansz", "dmeansz", "trans_depth", "res_bdy_len",
    "synack", "ackdat", "ct_state_ttl"
]

LIMITE_SEGUNDOS = 60


def criar_divisao_deterministica(ids_grupos, labels):
    base = pd.DataFrame({
        "grupo_id": list(ids_grupos),
        "Label": labels
    })

    resumo = base.groupby("grupo_id").agg(
        registros=("Label", "size"),
        normais=("Label", lambda x: (x == 0).sum()),
        ataques=("Label", lambda x: (x == 1).sum())
    )

    resumo = (
        resumo.reset_index()
        .sort_values(
            ["registros", "grupo_id"],
            ascending=[False, True],
            kind="mergesort"
        )
        .set_index("grupo_id")
    )

    proporcoes = np.array([0.70, 0.15, 0.15])

    totais = np.array([
        len(labels),
        (labels == 0).sum(),
        (labels == 1).sum()
    ])

    metas = proporcoes[:, None] * totais
    atuais = np.zeros((3, 3))
    atribuicao = {}

    primeiro_id = resumo.index[0]
    atribuicao[primeiro_id] = 0
    atuais[0] += resumo.iloc[0].to_numpy()

    for grupo_id, linha in resumo.iloc[1:].iterrows():
        valores = linha.to_numpy()
        melhor_destino = None
        menor_custo = float("inf")

        for destino in range(3):
            projetado = atuais.copy()
            projetado[destino] += valores

            custo = np.sum(((projetado - metas) / metas) ** 2)

            if custo < menor_custo:
                menor_custo = custo
                melhor_destino = destino

        atribuicao[grupo_id] = melhor_destino
        atuais[melhor_destino] += valores

    return np.array([atribuicao[g] for g in ids_grupos])


def criar_grupos(df_limpo):
    df_com_tempo = df_limpo[
        df_limpo["timestamp"].notna()
    ].copy()

    df_sem_tempo = df_limpo[
        df_limpo["timestamp"].isna()
    ].copy()

    df_ordenado = df_com_tempo.sort_values(
        COLUNAS_FLUXO + ["timestamp"]
    ).copy()

    df_ordenado["intervalo_segundos"] = (
        df_ordenado
        .groupby(COLUNAS_FLUXO, dropna=False)["timestamp"]
        .diff()
        .dt.total_seconds()
    )

    df_ordenado["grupo_fluxo"] = (
        df_ordenado
        .groupby(COLUNAS_FLUXO, dropna=False, sort=False)
        .ngroup()
    )

    inicio_sessao = (
        df_ordenado["intervalo_segundos"].isna()
        | (
            df_ordenado["intervalo_segundos"]
            > LIMITE_SEGUNDOS
        )
    )

    df_ordenado["sessao_60s"] = (
        inicio_sessao
        .groupby(df_ordenado["grupo_fluxo"])
        .cumsum()
    )

    chaves_com_tempo = set(
        map(
            tuple,
            df_com_tempo[COLUNAS_FLUXO]
            .astype(str)
            .drop_duplicates()
            .to_numpy()
        )
    )

    chaves_sem_tempo = set(
        map(
            tuple,
            df_sem_tempo[COLUNAS_FLUXO]
            .astype(str)
            .drop_duplicates()
            .to_numpy()
        )
    )

    sobreposicao = chaves_com_tempo & chaves_sem_tempo

    chaves_com = list(
        map(
            tuple,
            df_ordenado[COLUNAS_FLUXO]
            .astype(str)
            .to_numpy()
        )
    )

    chaves_sem = list(
        map(
            tuple,
            df_sem_tempo[COLUNAS_FLUXO]
            .astype(str)
            .to_numpy()
        )
    )

    grupos_com = []

    for chave, sessao in zip(
        chaves_com,
        df_ordenado["sessao_60s"]
    ):
        if chave in sobreposicao:
            grupo = ("fluxo_compartilhado", chave)
        else:
            grupo = ("sessao_temporal", chave, int(sessao))

        grupos_com.append(grupo)

    grupos_sem = []

    for chave in chaves_sem:
        if chave in sobreposicao:
            grupo = ("fluxo_compartilhado", chave)
        else:
            grupo = ("fluxo_sem_tempo", chave)

        grupos_sem.append(grupo)

    serie_com = pd.Series(
        grupos_com,
        index=df_ordenado.index
    )

    serie_sem = pd.Series(
        grupos_sem,
        index=df_sem_tempo.index
    )

    grupos_alinhados = pd.concat(
        [serie_com, serie_sem]
    ).reindex(df_limpo.index)

    if grupos_alinhados.isna().any():
        raise ValueError("Existem registros sem grupo identificado.")

    return grupos_alinhados


def executar(input_path: Path, output_dir: Path):
    print("Lendo dataset...")
    df = pd.read_csv(input_path, low_memory=False)

    total_original = len(df)

    print("Removendo duplicatas exatas...")
    df_limpo = df.drop_duplicates().copy()

    duplicatas = total_original - len(df_limpo)

    print("Convertendo Stime para timestamp...")

    stime_texto = df_limpo["Stime"].astype(str).str.strip()
    stime_numerico = pd.to_numeric(
        stime_texto,
        errors="coerce"
    )

    df_limpo["timestamp"] = pd.Series(
        pd.NaT,
        index=df_limpo.index,
        dtype="datetime64[ns, UTC]"
    )

    mask_unix = (
        stime_numerico.notna()
        & (stime_numerico != 0)
    )

    df_limpo.loc[mask_unix, "timestamp"] = pd.to_datetime(
        stime_numerico.loc[mask_unix],
        unit="s",
        errors="coerce",
        utc=True
    )

    mask_texto = stime_numerico.isna()

    df_limpo.loc[mask_texto, "timestamp"] = pd.to_datetime(
        df_limpo.loc[mask_texto, "Stime"],
        errors="coerce",
        utc=True
    )

    df_limpo["Label"] = pd.to_numeric(
        df_limpo["Label"],
        errors="raise"
    ).astype(int)

    if not set(df_limpo["Label"].unique()).issubset({0, 1}):
        raise ValueError("A coluna Label deve conter apenas 0 e 1.")

    colunas_necessarias = (
        COLUNAS_FLUXO + ["Stime", "Label"] + FEATURES
    )

    ausentes = [
        coluna for coluna in colunas_necessarias
        if coluna not in df_limpo.columns
    ]

    if ausentes:
        raise ValueError(
            f"Colunas necessárias ausentes: {ausentes}"
        )

    print("Criando grupos de fluxos e sessões...")
    grupos = criar_grupos(df_limpo)

    print("Distribuindo grupos entre treino, validação e teste...")
    divisao = criar_divisao_deterministica(
        grupos.tolist(),
        df_limpo["Label"].to_numpy()
    )

    nomes = {
        0: "treino",
        1: "validacao",
        2: "teste"
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    resumo = {
        "registros_originais": total_original,
        "duplicatas_removidas": duplicatas,
        "registros_finais": len(df_limpo),
        "grupos": int(grupos.nunique()),
        "limite_sessao_segundos": LIMITE_SEGUNDOS,
        "features": FEATURES,
        "divisoes": {}
    }

    for codigo, nome in nomes.items():
        indices = np.flatnonzero(divisao == codigo)

        parte = df_limpo.iloc[indices][
            FEATURES + ["Label"]
        ].copy()

        caminho = output_dir / f"{nome}.csv"
        parte.to_csv(caminho, index=False)

        resumo["divisoes"][nome] = {
            "registros": len(parte),
            "grupos": int(grupos.iloc[indices].nunique()),
            "normais": int((parte["Label"] == 0).sum()),
            "ataques": int((parte["Label"] == 1).sum())
        }

        print(f"\n{nome.upper()}:")
        print("Registros:", len(parte))
        print("Grupos:", resumo["divisoes"][nome]["grupos"])
        print("Classes:", parte["Label"].value_counts().to_dict())
        print("Arquivo:", caminho)

    grupos_por_divisao = {
        codigo: set(grupos.iloc[np.flatnonzero(divisao == codigo)])
        for codigo in nomes
    }

    assert not (
        grupos_por_divisao[0] & grupos_por_divisao[1]
    )
    assert not (
        grupos_por_divisao[0] & grupos_por_divisao[2]
    )
    assert not (
        grupos_por_divisao[1] & grupos_por_divisao[2]
    )

    assert sum(
        item["registros"]
        for item in resumo["divisoes"].values()
    ) == len(df_limpo)

    caminho_resumo = output_dir / "resumo_divisao.json"

    with caminho_resumo.open("w", encoding="utf-8") as arquivo:
        json.dump(
            resumo,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

    print("\nVERIFICAÇÕES:")
    print("Sobreposição entre grupos: nenhuma")
    print("Todos os registros foram distribuídos.")
    print("Total de grupos:", grupos.nunique())
    print("Resumo salvo em:", caminho_resumo)


def main():
    parser = argparse.ArgumentParser(
        description="Divisão agrupada do dataset para a IDS 9."
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Caminho do CSV original."
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed"),
        help="Diretório de saída."
    )

    args = parser.parse_args()

    executar(args.input, args.output_dir)


if __name__ == "__main__":
    main()
