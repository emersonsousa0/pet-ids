# Documentação Técnica e de Negócio: Análise de Pareto e Priorização de Ameaças (Issue IDS 6)

**Issue:** `[IDS 6]` Como analista de segurança, quero saber quais ataques concentram cerca de 80% do impacto na rede, para priorizar cenários de laboratório e foco do modelo.  
**Frente:** Frente ML / Segurança | **MoSCoW:** Must | **Estimativa:** M (3 pontos)  

---

## 1. Visão Geral

No desenvolvimento de um NIDS (*Network Intrusion Detection System*), a priorização de vetores de ameaça é essencial para:
1. **Otimizar os cenários de laboratório e testes de estresse**, garantindo que as simulações reflitam o perfil predominante e mais danoso do tráfego malicioso.
2. **Definir o foco e balanceamento do modelo de Machine Learning**, prevenindo sobreajuste em ruídos ou tráfegos minoritários e garantindo alta acurácia nas classes críticas.
3. **Atender ao Princípio de Pareto (80/20)**, identificando o grupo vital de ameaças que concentra cerca de 80% do impacto na rede.

---

## 2. Esclarecimento Metodológico: Rótulo do Dataset e Categorias Inferidas

> [!IMPORTANT]
> **Limitação Estrutural do Dataset Original:**
> O dataset utilizado (`Dataset_completo.csv` — origem Kaggle) é estritamente **binário** (`Label = 1` para ataque, `Label = 0` para benigno). O dataset **não traz rótulo categórico** especificando o nome ou tipo do ataque.

### Por que as categorias são "inferidas"?
A identificação de uma conexão TCP na porta 53, de um pacote ICMP ou de uma conexão HTTP na porta 80 **não comprova isoladamente** a ocorrência de um ataque específico (como ICMP Flood ou SQLi).

No entanto, uma vez que o registro **já foi previamente rotulado como malicioso (`Label == 1`)**, é realizada uma **inferência comportamental baseada em protocolo de transporte (`proto`) e porta de destino (`dsport`)**:
- `ICMP Flood / Ping Sweep (ICMP)`: `proto` normalizado como `ICMP (1)`.
- `TCP Porta 53 (DNS / Flood)`: `proto` normalizado como `TCP (6)` na porta `53`.
- `Web / HTTP (Portas 80/8180/8009)`: `proto` normalizado como `TCP (6)` nas portas `80`, `8180` ou `8009`.
- `FTP / Brute Force (Porta 21)`: `proto` normalizado como `TCP (6)` na porta `21`.
- `TCP Varredura / Port Scan (Port Scan)`: `proto` normalizado como `TCP (6)` nas demais portas.
- `Tráfego UDP (Portas Diversas)`: `proto` normalizado como `UDP (17)`.
- `Registros Anômalos / Zerados (Proto 0)`: `proto` igual a `0` / `0.0` (`HOPOPT/Zero (0)`).
- `Outros Protocolos (IPv6-ICMP/IGMP)`: demais protocolos após normalização.

Essa distinção garante transparência técnica: as classes representam perfis inferidos de tráfego malicioso observado, e não rótulos nativos do dataset.

---

## 3. Metodologia de Cálculo de Impacto e Critérios CIA

Para atender ao requisito de **impacto**, o script `paretoAnalysis/ParetoCalculation.py` calcula o **Impacto CIA** como métrica principal e também registra a **Frequência** e o **Volume de Dados (`sbytes + dbytes`)** de cada categoria inferida.

### 3.1. Métrica Principal: Impacto CIA (`Frequência × Score_CIA`)
A severidade técnica é definida em `PESOS_CIA` a partir dos pilares **Confidencialidade (`C`)**, **Integridade (`I`)** e **Disponibilidade (`A`)** (escala de 1 a 5 por dimensão):

$$\text{Score\_CIA} = C + I + A$$

$$\text{Impacto\_CIA} = \text{Frequência} \times \text{Score\_CIA}$$

#### Atribuição de Pesos CIA por Categoria Inferida:
| Categoria Inferida | C | I | A | Score_CIA | Justificativa do Impacto |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `ICMP Flood / Ping Sweep (ICMP)` | 1 | 1 | 5 | **7** | Foco em disponibilidade (`A=5`) por saturação/flood ou varredura de hosts. |
| `TCP Porta 53 (DNS / Flood)` | 1 | 1 | 5 | **7** | Foco em disponibilidade (`A=5`) por impacto na resolução de nomes. |
| `TCP Varredura / Port Scan (Port Scan)` | 2 | 1 | 1 | **4** | Leve exposição de informações de rede (`C=2`) em sondagem de portas. |
| `Web / HTTP (Portas 80/8180/8009)` | 4 | 4 | 3 | **11** | Alto potencial de impacto em confidencialidade e integridade de serviços web, com efeito moderado em disponibilidade. |
| `FTP / Brute Force (Porta 21)` | 4 | 3 | 2 | **9** | Risco relevante para credenciais/dados (`C=4`) e arquivos/integridade (`I=3`). |
| `Tráfego UDP (Portas Diversas)` | 1 | 1 | 3 | **5** | Impacto moderado em disponibilidade (`A=3`) em tráfego sem conexão. |
| `Registros Anômalos / Zerados (Proto 0)` | 1 | 1 | 1 | **3** | Severidade base mínima para registros com protocolo zerado/incompleto. |
| `Outros Protocolos (IPv6-ICMP/IGMP)` | 1 | 1 | 1 | **3** | Severidade base mínima para fluxos residuais de outros protocolos. |

### 3.2. Métricas Auxiliares
- **Frequência (`Frequencia`):** contagem de registros maliciosos (`Label == 1`) em cada categoria inferida.
- **Volume de Dados (`Volume_Bytes`):** soma de `sbytes + dbytes` para os registros maliciosos da categoria (com `Porcentagem_Volume` e `Acumulada_Volume` calculadas no CSV).

---

## 4. Resultados Consolidados da Análise de Pareto

O dataset completo contém **368.017 registros**, sendo **336.735 registros maliciosos (91,50%)**. A análise incide estritamente sobre essa fatia hostil.

### 4.1. Tabela Comparativa de Pareto 

| Ranking CIA | Categoria Inferida | Score CIA | Impacto CIA | % Rel (CIA) | % Acum (CIA) | Prioritário (Top 80% CIA) | Frequência | % Acum (Freq) | Volume (Bytes) | % Acum (Vol) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1º** | **ICMP Flood / Ping Sweep (ICMP)** | 7 | 926.702 | 44,54% | **44,54%** | **SIM** | 132.386 | 39,31% | 3.754 | 100,00% |
| **2º** | **TCP Porta 53 (DNS / Flood)** | 7 | 682.367 | 32,80% | **77,34%** | **SIM** | 97.481 | 68,26% | 5.379.509 | 99,80% |
| **3º** | **TCP Varredura / Port Scan (Port Scan)** | 4 | 338.232 | 16,26% | **93,60%** | **SIM** | 84.558 | 93,37% | 7.644.061 | 98,97% |
| 4º | Web / HTTP (Portas 80/8180/8009) | 11 | 45.210 | 2,17% | 95,77% | NÃO | 4.110 | 98,77% | 637.251.289 | 97,80% |
| 5º | FTP / Brute Force (Porta 21) | 9 | 32.652 | 1,57% | 97,34% | NÃO | 3.628 | 99,85% | 339.726 | 99,99% |
| 6º | Tráfego UDP (Portas Diversas) | 5 | 28.975 | 1,39% | 98,73% | NÃO | 5.795 | 97,55% | 909.605 | 99,93% |
| 7º | Registros Anômalos / Zerados (Proto 0) | 3 | 24.810 | 1,19% | 99,93% | NÃO | 8.270 | 95,83% | 0 | 100,00% |
| 8º | Outros Protocolos (IPv6-ICMP/IGMP) | 3 | 1.521 | 0,07% | 100,00% | NÃO | 507 | 100,00% | 82.352 | 100,00% |

---

## 5. Interpretação dos Resultados e Recomendações

### 5.1. Comparação entre Impacto CIA, Frequência e Volume
1. **Peso do Impacto CIA e da Frequência:**
   - As três primeiras categorias concentram **93,60%** de `Acumulada_Impacto` e **234.425** dos **336.735** fluxos maliciosos (**69,62%** somando `132.386 + 97.481` nas duas primeiras, e **93,37%** somando `84.558` da terceira).
   - Os dois primeiros colocados combinam alto volume com disponibilidade (`A = 5`), elevando seu `Impacto_CIA`.
2. **Diferença em relação ao Volume (`Volume_Bytes`):**
   - `Web / HTTP (Portas 80/8180/8009)` concentra a maior parte dos bytes transferidos (`637.251.289` bytes), apesar de ter frequência bem menor (`4.110` registros).
   - Avaliar apenas `Volume_Bytes` daria peso maior a fluxos volumosos e subestimaria floods e varreduras com pacotes menores.

### 5.2. Lista de Ataques Prioritários Aprovada
Com base no corte de Pareto (`Prioritario_80_20 == True`), o grupo prioritário para laboratório e foco do modelo é:

1. **`ICMP Flood / Ping Sweep (ICMP)`** (`44,54%` do impacto CIA; `132.386` registros): priorizar cenários de saturação de enlace/flood ICMP e detecção de sondagens em massa.
2. **`TCP Porta 53 (DNS / Flood)`** (`32,80%` do impacto CIA; `97.481` registros): priorizar testes envolvendo tráfego e anomalias/flood direcionados à porta 53.
3. **`TCP Varredura / Port Scan (Port Scan)`** (`16,26%` do impacto CIA; `84.558` registros): priorizar cenários de varredura de portas TCP em destinos variados para mapear a rede.