from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

# Nota: o dataset original possui apenas rótulo binário (Label: 0 = benigno, 1 = malicioso).
# As categorias abaixo são inferidas por heurística a partir de protocolo (proto) e porta (dsport),
# não comprovando isoladamente a ocorrência de um ataque específico.
PESOS_CIA = {
    "ICMP Flood / Ping Sweep (ICMP)": {"C": 1, "I": 1, "A": 5},
    "TCP Porta 53 (DNS / Flood)": {"C": 1, "I": 1, "A": 5},
    "TCP Varredura / Port Scan (Port Scan)": {"C": 2, "I": 1, "A": 1},
    "Web / HTTP (Portas 80/8180/8009)": {"C": 4, "I": 4, "A": 3},
    "FTP / Brute Force (Porta 21)": {"C": 4, "I": 3, "A": 2},
    "Tráfego UDP (Portas Diversas)": {"C": 1, "I": 1, "A": 3},
    "Registros Anômalos / Zerados (Proto 0)": {"C": 1, "I": 1, "A": 1},
    "Outros Protocolos (IPv6-ICMP/IGMP)": {"C": 1, "I": 1, "A": 1},
}

# 1. Carregamento e limpeza básica dos cabeçalhos
base_dir = Path(__file__).resolve().parent
caminho_csv = base_dir / "datasets" / "Dataset_completo.csv"
df = pd.read_csv(caminho_csv, low_memory=False)
df.columns = df.columns.str.strip()

# 2. Diagnóstico geral (Benigno vs Malicioso)
total_registros = len(df)
df_mal = df[df["Label"] == 1].copy()
df_ben = df[df["Label"] == 0].copy()

print("=== DIAGNÓSTICO GERAL DO DATASET ===")
print(f"Total de registros : {total_registros}")
print(
    f"Maliciosos (Label=1): {len(df_mal)}"
    f" ({len(df_mal)/total_registros*100:.2f}%)"
)
print(
    f"Benignos   (Label=0): {len(df_ben)}"
    f" ({len(df_ben)/total_registros*100:.2f}%)\n"
)


# 3. Normalização da coluna de protocolo (unifica '6', '6.0', 'TCP', etc.)
def normalizar_protocolo(val):
    v = str(val).strip().upper()
    if v in ["6", "6.0", "TCP"]:
        return "TCP (6)"
    if v in ["1", "1.0", "ICMP"]:
        return "ICMP (1)"
    if v in ["17", "17.0", "UDP"]:
        return "UDP (17)"
    if v in ["0", "0.0"]:
        return "HOPOPT/Zero (0)"
    return v


df_mal["proto_norm"] = df_mal["proto"].apply(normalizar_protocolo)
df_mal["dsport_num"] = pd.to_numeric(df_mal["dsport"], errors="coerce")

sbytes = pd.to_numeric(df_mal.get("sbytes"), errors="coerce").fillna(0)
dbytes = pd.to_numeric(df_mal.get("dbytes"), errors="coerce").fillna(0)
df_mal["volume_bytes"] = sbytes + dbytes


# 4. Perfilamento técnico por Protocolo + Porta de Destino (dsport)
def classificar_padrao_ataque(row):
    p = row["proto_norm"]
    port = row["dsport_num"]

    if p == "ICMP (1)":
        return "ICMP Flood / Ping Sweep (ICMP)"
    if p == "TCP (6)" and port == 53:
        return "TCP Porta 53 (DNS / Flood)"
    if p == "TCP (6)" and port in [80, 8180, 8009]:
        return "Web / HTTP (Portas 80/8180/8009)"
    if p == "TCP (6)" and port == 21:
        return "FTP / Brute Force (Porta 21)"
    if p == "TCP (6)":
        return "TCP Varredura / Port Scan (Port Scan)"
    if p == "HOPOPT/Zero (0)":
        return "Registros Anômalos / Zerados (Proto 0)"
    if p == "UDP (17)":
        return "Tráfego UDP (Portas Diversas)"
    return "Outros Protocolos (IPv6-ICMP/IGMP)"


df_mal["Categoria_Observada"] = df_mal.apply(classificar_padrao_ataque, axis=1)

# 5. Cálculo da Tabela de Pareto Comparativa (Impacto CIA, Frequência e Volume)
resumo = (
    df_mal.groupby("Categoria_Observada", as_index=False)
    .agg(
        Frequencia=("Categoria_Observada", "count"),
        Volume_Bytes=("volume_bytes", "sum"),
    )
)

resumo["Score_CIA"] = resumo["Categoria_Observada"].map(
    lambda c: PESOS_CIA[c]["C"] + PESOS_CIA[c]["I"] + PESOS_CIA[c]["A"]
)
resumo["Impacto_CIA"] = resumo["Frequencia"] * resumo["Score_CIA"]

# Acumulados individuais ordenados por cada métrica (Frequência e Volume)
resumo = resumo.sort_values("Frequencia", ascending=False)
resumo["Pct_Acum_Freq"] = (resumo["Frequencia"] / resumo["Frequencia"].sum() * 100).cumsum()

resumo = resumo.sort_values("Volume_Bytes", ascending=False)
resumo["Pct_Acum_Vol"] = (resumo["Volume_Bytes"] / resumo["Volume_Bytes"].sum() * 100).cumsum()

# Ordenação final pela métrica principal: Impacto CIA
resumo = resumo.sort_values("Impacto_CIA", ascending=False).reset_index(drop=True)
pct_rel_cia = (resumo["Impacto_CIA"] / resumo["Impacto_CIA"].sum()) * 100
pct_acum_cia = pct_rel_cia.cumsum()
prioritario_cia = pct_acum_cia.shift(1, fill_value=0) < 80.0

tabela_pareto = pd.DataFrame({
    "Ranking CIA": [f"{i + 1}º" for i in range(len(resumo))],
    "Categoria Inferida": resumo["Categoria_Observada"],
    "Score CIA": resumo["Score_CIA"],
    "Impacto CIA": resumo["Impacto_CIA"],
    "% Rel (CIA)": pct_rel_cia.map(lambda x: f"{x:.2f}%"),
    "% Acum (CIA)": pct_acum_cia.map(lambda x: f"{x:.2f}%"),
    "Prioritário (Top 80% CIA)": prioritario_cia.map(lambda p: "SIM" if p else "NÃO"),
    "Frequência": resumo["Frequencia"],
    "% Acum (Freq)": resumo["Pct_Acum_Freq"].map(lambda x: f"{x:.2f}%"),
    "Volume (Bytes)": resumo["Volume_Bytes"].astype(int),
    "% Acum (Vol)": resumo["Pct_Acum_Vol"].map(lambda x: f"{x:.2f}%"),
})

print("=== ANÁLISE DE PARETO POR IMPACTO CIA (TRÁFEGO MALICIOSO) ===")
print(tabela_pareto.to_string(index=False))

tabela_pareto.to_csv(base_dir / "tabela_pareto_dataset_completo.csv", index=False)

# 6. Geração do Gráfico de Pareto
fig, ax1 = plt.subplots(figsize=(10, 5.5))

ax1.bar(
    resumo["Categoria_Observada"],
    resumo["Impacto_CIA"],
    color="#2b5c8f",
    alpha=0.85,
    label="Impacto CIA (Frequência x Score_CIA)",
)
ax1.set_ylabel("Impacto CIA", color="#2b5c8f", fontweight="bold")
ax1.tick_params(axis="x", rotation=30)
plt.setp(ax1.get_xticklabels(), ha="right")

ax2 = ax1.twinx()
ax2.plot(
    resumo["Categoria_Observada"],
    pct_acum_cia,
    color="#d95f02",
    marker="o",
    linewidth=2.5,
    label="% Acumulada de Impacto",
)
ax2.axhline(
    80, color="red", linestyle="--", linewidth=1.2, label="Corte Pareto (80%)"
)
ax2.set_ylabel("Porcentagem Acumulada (%)", color="#d95f02", fontweight="bold")
ax2.set_ylim(0, 105)

for i, val in enumerate(pct_acum_cia):
    ax2.annotate(
        f"{val:.1f}%",
        (i, val + 2.5),
        ha="center",
        fontsize=8.5,
        fontweight="bold",
        color="#a63603",
    )

plt.title(
    "Análise de Pareto por Impacto CIA - Perfil do Tráfego Malicioso (Dataset_completo.csv)",
    fontweight="bold",
)
ax2.legend(loc="center right")
plt.tight_layout()

plt.savefig(base_dir / "pareto_dataset_completo.png", dpi=150)
plt.show()