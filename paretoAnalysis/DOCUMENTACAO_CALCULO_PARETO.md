(all agent edits)
# Documentação Técnica e de Negócio: Análise de Pareto e Priorização de Ataques (Issue IDS 6)
**Issue:** `[IDS 6]` Como analista de segurança, quero saber quais ataques concentram cerca de 80% do impacto na rede, para priorizar cenários de laboratório e foco do modelo.  
**Frente:** Frente ML | **MoSCoW:** Must | **Estimativa:** M (3 pontos)  
---
## 1. Visão Geral e Contexto da Issue
Dentro do ciclo de desenvolvimento do modelo de NIDS (*Network Intrusion Detection System*), a priorização de vetores de ameaça é fundamental para:
1. **Otimizar cenários de laboratório e testes de estresse**, garantindo que as simulações reflitam o perfil predominante de tráfego hostil.
2. **Definir o foco e balanceamento do modelo de Machine Learning**, assegurando que os algoritmos de detecção capturem as classes de maior representatividade estatística e relevância operacional sem serem ofuscados por ruído.
3. **Atender ao Princípio de Pareto (80/20)**, identificando o subconjunto vital de ataques (~20% das classes) responsável por aproximadamente 80% do tráfego malicioso na rede.
---
## 2. Fundamentação Teórica e Matriz de Impacto (CIA)
O mapeamento técnico utilizou como base o documento **[Levantamento Teórico e Matriz de Impacto.pdf]**, que classifica os ataques de rede em 6 grandes vetores e pondera o impacto nos três pilares da segurança da informação (Confidencialidade, Integridade e Disponibilidade — escala de 1 a 5):
| Categoria | Vetor de Ataque | Confidencialidade (C) | Integridade (I) | Disponibilidade (A) | Justificativa do Impacto Principal |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **1. Reconhecimento** | Port Scanning / Host Discovery | 2 | 1 | 1 | Expõe a topologia e portas/serviços ativos, mapeando alvos para fases posteriores. |
| **1. Reconhecimento** | Fingerprinting | 3 | 1 | 1 | Revela versões exatas de SO/software para exploração direcionada. |
| **2. Negação de Serviço** | SYN / ICMP / UDP Flood | 1 | 1 | 5 | Esgota largura de banda e capacidade de processamento, causando indisponibilidade massiva. |
| **3. Protocolos / Rede** | IP / ARP Spoofing, Hijacking | 2–5 | 2–5 | 2–3 | Falsificação de pacotes, desvio de sessões e MitM. |
| **4. Exploits / Malware**| Buffer Overflow, Worms, Shellcode | 3–5 | 4–5 | 4–5 | Comprometimento total da máquina com execução remota de código (RCE). |
| **5. Aplicação** | SQLi, Directory Traversal, Brute Force | 4–5 | 2–5 | 1–4 | Violação de integridade de banco de dados e autenticação forçada em serviços (ex: FTP/HTTP). |
| **6. Evasão** | Fragmentação / Ofuscação | 1 | 1 | 1 | Multiplicador de risco que busca ocultar ataques de alto impacto. |
---
## 3. Metodologia de Cálculo e Implementação ([ParetoCalculation.py])
O script de processamento em Python opera sobre o dataset completo rotulado (`Dataset_completo.csv`), implementando as seguintes etapas:
### 3.1. Diagnóstico Geral do Dataset
- Separação entre tráfego benigno (`Label == 0`) e malicioso (`Label == 1`).
- **Filtro de Análise:** A análise de Pareto é restrita estritamente ao tráfego malicioso (`df_mal`), totalizando **336.735 registros maliciosos**.
### 3.2. Normalização e Perfilamento Técnico
Devido a variações de representação no fluxo de rede (ex.: protocolos numéricos e textuais), implementou-se a normalização:
- **Protocolos:** Tratamento unificado de `TCP (6)`, `ICMP (1)`, `UDP (17)` e `HOPOPT/Zero (0)`.
- **Heurística de Mapeamento (`classificar_padrao_ataque`):** Cruza protocolo com porta de destino (`dsport`):
  - `ICMP (1)` $\rightarrow$ **ICMP Flood / Ping Sweep (ICMP)**
  - `TCP (6)` com `dsport == 53` $\rightarrow$ **TCP Porta 53 (DNS / Flood)**
  - `TCP (6)` genérico/outras portas $\rightarrow$ **TCP Varredura / Outras Portas (Port Scan)**
  - `TCP (6)` nas portas `80, 8180, 8009` $\rightarrow$ **Web / HTTP (Portas 80/8180/8009)**
  - `TCP (6)` na porta `21` $\rightarrow$ **FTP / Brute Force (Porta 21)**
  - `UDP (17)` $\rightarrow$ **Tráfego UDP (Portas Diversas)**
  - Protocolo `0` $\rightarrow$ **Registros Anômalos / Zerados (Proto 0)**
  - Outros $\rightarrow$ **Outros Protocolos (IPv6-ICMP/IGMP)**
### 3.3. Cálculo da Curva Cumulativa e Linha de Corte
Calcula-se a frequência absoluta, percentual relativo e a porcentagem acumulada. O corte de 80% identifica as classes vitais que atingem e superam a linha de 80% acumulados.
---
## 4. Resultados da Análise de Pareto
### 4.1. Tabela Consolidada ([tabela_pareto_dataset_completo.csv])
| Ranking | Categoria Observada | Frequência (Registros) | % Relativa | % Acumulada | Prioritário (Corte 80/20) |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1º** | **ICMP Flood / Ping Sweep (ICMP)** | 132.386 | 39,31% | **39,31%** | **SIM** |
| **2º** | **TCP Porta 53 (DNS / Flood)** | 97.481 | 28,95% | **68,26%** | **SIM** |
| **3º** | **TCP Varredura / Outras Portas (Port Scan)** | 84.558 | 25,11% | **93,37%** | **SIM** |
| 4º | Registros Anômalos / Zerados (Proto 0) | 8.270 | 2,46% | 95,83% | NÃO |
| 5º | Tráfego UDP (Portas Diversas) | 5.795 | 1,72% | 97,55% | NÃO |
| 6º | Web / HTTP (Portas 80/8180/8009) | 4.110 | 1,22% | 98,77% | NÃO |
| 7º | FTP / Brute Force (Porta 21) | 3.628 | 1,08% | 99,85% | NÃO |
| 8º | Outros Protocolos (IPv6-ICMP/IGMP) | 507 | 0,15% | 100,00% | NÃO |
### 4.2. Gráfico de Pareto Gerado
O gráfico gerado pelo script demonstra a distribuição de cauda longa típica de redes corporativas/laboratórios:
- **As 3 primeiras categorias** concentram **93,37%** de todo o tráfego malicioso registrado no dataset.
- As demais 5 categorias somadas representam apenas **6,63%** do volume de eventos hostis.
---
## 5. Critérios de Aceitação e Conclusões da Issue [IDS 6]
### Verificação dos Critérios de Aceitação
- [x] **Dado o dataset rotulado:** Utilizado o `Dataset_completo.csv` com diagnóstico de tráfego malicioso (`Label == 1`).
- [x] **Métrica de impacto definida:** Frequência de ocorrência volumétrica aliada à Matriz Teórica CIA (impacto em Disponibilidade e Confidencialidade).
- [x] **Cálculo do ranking e curva de Pareto:** Executado via `ParetoCalculation.py`, gerando CSV e gráfico padronizado.
- [x] **Lista de ataques prioritários aprovada:**
  1. **ICMP Flood / Ping Sweep** (Disponibilidade/Reconhecimento — 39,31%)
  2. **TCP Porta 53 / Flood** (Disponibilidade/Serviços Críticos — 28,95%)
  3. **TCP Port Scan / Varredura** (Reconhecimento/Mapeamento — 25,11%)