# IDS 9 — Divisão agrupada do dataset

## 1. Objetivo

Implementar uma divisão determinística dos dados em treino, validação e teste, evitando que fluxos de rede semelhantes apareçam em conjuntos diferentes e provoquem vazamento de dados (*data leakage*).

A divisão foi desenvolvida com base em grupos de fluxos e sessões temporais, preservando a distribuição das classes.

## 2. Tratamento dos dados

O dataset original continha 368.017 registros.

Após a remoção de duplicatas exatas, foram mantidos 362.445 registros, com 5.572 duplicatas removidas.

A coluna `Stime` foi convertida para timestamp, considerando valores Unix e datas em formato textual. Registros sem timestamp válido foram mantidos.

## 3. Estratégia de agrupamento

Foram utilizados os seguintes campos para identificar os fluxos:

- `srcip`
- `sport`
- `dstip`
- `dsport`
- `proto`

Para registros com timestamp válido, foi adotado um limite de 60 segundos entre registros consecutivos do mesmo fluxo. Intervalos superiores a esse limite iniciam uma nova sessão.

O limite de 60 segundos é uma heurística adotada neste experimento, não uma definição universal de sessão de rede.

Para registros sem timestamp, foi utilizado o agrupamento pelo conjunto de campos do fluxo.

Quando uma mesma chave aparecia tanto em registros com timestamp quanto sem timestamp, os registros foram mantidos no mesmo grupo, evitando a separação entre conjuntos.

Resultado: **74.117 grupos**, distribuídos em:

- 338.730 registros em sessões temporais;
- 15.767 registros em fluxos compartilhados;
- 7.948 registros em fluxos sem timestamp.

Foram identificados 25 grupos contendo registros das duas classes.

## 4. Divisão dos dados

Foi implementado um algoritmo determinístico de distribuição de grupos, buscando aproximar as proporções de 70% para treino, 15% para validação e 15% para teste, preservando também a distribuição das classes.

| Conjunto | Registros | Grupos | Normais | Ataques |
|---|---:|---:|---:|---:|
| Treino | 253.711 | 54.991 | 19.016 | 234.695 |
| Validação | 54.367 | 9.562 | 4.075 | 50.292 |
| Teste | 54.367 | 9.564 | 4.075 | 50.292 |
| **Total** | **362.445** | **74.117** | **27.166** | **335.279** |

A distribuição das classes permaneceu aproximadamente igual nos três conjuntos: 7,5% de registros normais e 92,5% de ataques.

## 5. Remoção de identificadores e seleção de atributos

Foram removidos os seguintes campos:

- `srcip`, `sport`, `dstip` e `dsport`;
- `Stime` e `Ltime`;
- `timestamp`;
- `stcpb` e `dtcpb`, por serem números de sequência TCP associados à conexão;
- `is_sm_ips_ports`, por apresentar valor constante no conjunto de treino.

Foram mantidas 19 features para utilização posterior nos modelos de aprendizado de máquina:

`proto`, `state`, `dur`, `sbytes`, `dbytes`, `sttl`, `service`, `Sload`, `Dload`, `Spkts`, `Dpkts`, `swin`, `smeansz`, `dmeansz`, `trans_depth`, `res_bdy_len`, `synack`, `ackdat` e `ct_state_ttl`.

A etapa de codificação de variáveis categóricas e pré-processamento para os classificadores não faz parte desta tarefa.

## 6. Verificações realizadas

Foram realizadas as seguintes verificações:

- Reprodutibilidade da divisão, executada duas vezes com o mesmo resultado.
- Ausência de grupos compartilhados entre treino e validação.
- Ausência de grupos compartilhados entre treino e teste.
- Ausência de grupos compartilhados entre validação e teste.
- Distribuição de todos os 74.117 grupos.
- Distribuição de todos os 362.445 registros.
- Remoção das colunas identificadoras da matriz de features.

Todas as verificações foram aprovadas.

## 7. Arquivos gerados

O script `scripts/divide_dataset.py` implementa o processo completo.

Os arquivos gerados são:

- `treino.csv`
- `validacao.csv`
- `teste.csv`
- `resumo_divisao.json`

Os resultados são salvos, por padrão, no diretório `data/processed/`, mantido fora do versionamento pelo `.gitignore`.

## 8. Limitações e observações

A divisão por grupos reduz o risco de vazamento entre fluxos semelhantes, mas não garante ausência de qualquer correlação entre registros de redes diferentes.

O limite de 60 segundos foi escolhido com base nas análises exploratórias realizadas no dataset. Também foi identificada uma sessão muito grande, com 131.043 registros, associada a um fluxo ICMP de ataque. Esse grupo foi mantido unido para respeitar a estratégia de prevenção de vazamento.

O treinamento e a comparação entre classificadores serão realizados em tarefas posteriores, especialmente na IDS 10.