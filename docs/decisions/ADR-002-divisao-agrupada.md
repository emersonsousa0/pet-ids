# ADR-002 — Divisão dos dados por grupos de fluxos

- **Status:** Aceita
- **Data:** 25/11/2026
- **Contexto:** IDS 9 — Prevenção de vazamento de dados

## Contexto

A divisão aleatória convencional de registros pode fazer com que fluxos de rede semelhantes apareçam simultaneamente nos conjuntos de treino, validação e teste.

Isso pode provocar vazamento de dados e produzir métricas de avaliação artificialmente elevadas.

## Decisão

Adotar uma divisão agrupada e determinística, utilizando os campos `srcip`, `sport`, `dstip`, `dsport` e `proto` para identificar fluxos.

Para registros com timestamp válido, os fluxos serão subdivididos em sessões temporais, considerando um intervalo de 60 segundos entre registros consecutivos.

Registros sem timestamp serão agrupados pelas mesmas chaves de fluxo. Quando houver correspondência entre registros com e sem timestamp, eles permanecerão no mesmo grupo.

A distribuição será realizada buscando as proporções de 70% para treino, 15% para validação e 15% para teste, preservando a distribuição das classes.

Os identificadores e campos associados à conexão serão removidos das features utilizadas pelos modelos.

## Consequências

- Redução do risco de vazamento entre os conjuntos.
- Reprodutibilidade da divisão.
- Preservação da distribuição das classes.
- Possibilidade de conjuntos com pequenas diferenças em relação às proporções desejadas, devido à necessidade de manter grupos inteiros.
- A sessão temporal de 60 segundos representa uma heurística específica deste experimento.

## Implementação

A implementação está em `scripts/divide_dataset.py`.

Os resultados experimentais estão documentados em `docs/experimentos/ids-09-divisao-agrupada.md`.