import matplotlib.pyplot as plt
import pandas as pd

# 1. Carregamento e limpeza básica dos cabeçalhos
caminho_csv = "Dataset_completo.csv"
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


# 4. Perfilamento técnico por Protocolo + Porta de Destino (dsport)
def classificar_padrao_ataque(row):
    p = row["proto_norm"]
    port = row["dsport"]

    if p == "ICMP (1)":
        return "ICMP Flood / Ping Sweep (ICMP)"
    if p == "TCP (6)" and port == 53.0:
        return "TCP Porta 53 (DNS / Flood)"
    if p == "TCP (6)" and port in [80.0, 8180.0, 8009.0]:
        return "Web / HTTP (Portas 80/8180/8009)"
    if p == "TCP (6)" and port == 21.0:
        return "FTP / Brute Force (Porta 21)"
    if p == "TCP (6)":
        return "TCP Varredura / Outras Portas (Port Scan)"
    if p == "HOPOPT/Zero (0)":
        return "Registros Anômalos / Zerados (Proto 0)"
    if p == "UDP (17)":
        return "Tráfego UDP (Portas Diversas)"
    return "Outros Protocolos (IPv6-ICMP/IGMP)"


df_mal["Categoria_Observada"] = df_mal.apply(classificar_padrao_ataque, axis=1)

# 5. Cálculo da Tabela de Pareto e Corte 80/20
pareto = df_mal["Categoria_Observada"].value_counts().reset_index()
pareto.columns = ["Categoria_Observada", "Frequencia"]
pareto["Porcentagem"] = (pareto["Frequencia"] / pareto["Frequencia"].sum()) * 100
pareto["Acumulada"] = pareto["Porcentagem"].cumsum()

# Marca como prioritário até atingir/ultrapassar a linha dos 80%
pareto["Prioritario_80_20"] = pareto["Acumulada"].shift(1, fill_value=0) < 80.0

print("=== ANÁLISE DE PARETO (TRÁFEGO MALICIOSO) ===")
print(pareto.to_string(index=False))

pareto.to_csv("tabela_pareto_dataset_completo.csv", index=False)

# 6. Geração do Gráfico de Pareto
fig, ax1 = plt.subplots(figsize=(10, 5.5))

ax1.bar(
    pareto["Categoria_Observada"],
    pareto["Frequencia"],
    color="#2b5c8f",
    alpha=0.85,
    label="Frequência",
)
ax1.set_ylabel("Frequência (Nº de Registros)", color="#2b5c8f", fontweight="bold")
ax1.tick_params(axis="x", rotation=30)
plt.setp(ax1.get_xticklabels(), ha="right")

ax2 = ax1.twinx()
ax2.plot(
    pareto["Categoria_Observada"],
    pareto["Acumulada"],
    color="#d95f02",
    marker="o",
    linewidth=2.5,
    label="% Acumulada",
)
ax2.axhline(
    80, color="red", linestyle="--", linewidth=1.2, label="Corte Pareto (80%)"
)
ax2.set_ylabel("Porcentagem Acumulada (%)", color="#d95f02", fontweight="bold")
ax2.set_ylim(0, 105)

for i, val in enumerate(pareto["Acumulada"]):
    ax2.annotate(
        f"{val:.1f}%",
        (i, val + 2.5),
        ha="center",
        fontsize=8.5,
        fontweight="bold",
        color="#a63603",
    )

plt.title(
    "Análise de Pareto - Perfil do Tráfego Malicioso (Dataset_completo.csv)",
    fontweight="bold",
)
ax2.legend(loc="center right")
plt.tight_layout()

plt.savefig("pareto_dataset_completo.png", dpi=150)
plt.show()