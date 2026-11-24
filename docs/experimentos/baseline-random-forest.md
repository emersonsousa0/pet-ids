# Baseline de classificação com Random Forest

## 1. Objetivo

Desenvolver um modelo inicial de classificação para a tarefa SCRUM-21 do projeto PET-IDS, utilizando Random Forest dentro de um Pipeline do Scikit-learn.

O objetivo é identificar fluxos de rede benignos e fluxos associados a ataques, estabelecendo métricas de referência para futuras comparações.

## 2. Dataset utilizado

Foi escolhido o arquivo `Dataset_resumido.csv`, por apresentar um volume menor de dados e permitir uma execução mais simples durante o desenvolvimento do baseline.

A variável-alvo utilizada foi `Label`:

- `0`: tráfego benigno.
- `1`: tráfego de ataque.

Foram selecionados somente os registros que possuem valor preenchido na coluna `dur`.

| Informação | Quantidade |
|---|---:|
| Registros selecionados | 32.672 |
| Registros de treinamento | 26.137 |
| Registros de teste | 6.535 |
| Fluxos benignos | 5.746 |
| Fluxos de ataque | 26.926 |

O conjunto selecionado apresenta aproximadamente 17,59% de registros benignos e 82,41% de ataques.

## 3. Variáveis utilizadas

Foram utilizadas duas categorias de variáveis.

**Variáveis numéricas:**

- `dur`
- `sbytes`
- `dbytes`
- `Sload`
- `Dload`
- `Spkts`
- `Dpkts`
- `smeansz`
- `dmeansz`

O tratamento dos valores ausentes dessas variáveis utiliza `SimpleImputer`, com preenchimento pela mediana.

**Variáveis categóricas:**

- `proto`
- `state`

O pré-processamento utiliza `SimpleImputer`, com preenchimento pelo valor mais frequente, e `OneHotEncoder`, para transformar categorias em representações numéricas.

### Variáveis excluídas

| Variável | Justificativa |
|---|---|
| `service` | Apresenta aproximadamente 75,84% de valores ausentes no recorte e forte associação entre ausência e classe. Será avaliada em experimento futuro. |
| `ct_state_ttl` | Decisão de utilização ainda pendente no contrato de features. |
| `trans_depth` | Está totalmente ausente no recorte utilizado. |
| `res_bdy_len` | Está totalmente ausente no recorte utilizado. |
| `is_sm_ips_ports` | Apresenta valor constante no recorte. |

A exclusão de `service` representa uma decisão experimental conservadora. A associação observada não comprova, por si só, a existência de vazamento de dados.

## 4. Modelo e configuração

Foi utilizado o algoritmo `RandomForestClassifier`, integrado a um `Pipeline`.

| Parâmetro | Valor |
|---|---|
| `n_estimators` | 200 |
| `class_weight` | balanced |
| `random_state` | 42 |
| `n_jobs` | -1 |

O parâmetro `class_weight="balanced"` ajusta os pesos das classes conforme sua frequência nos dados de treinamento.

O Pipeline reúne o pré-processamento e o classificador, garantindo que as mesmas transformações sejam aplicadas durante o treinamento e nas previsões futuras.

## 5. Treinamento e avaliação

A divisão dos dados foi realizada de maneira estratificada:

- 80% dos registros para treinamento.
- 20% dos registros para teste.
- `random_state=42`, para permitir a reprodução da divisão.

Foram calculadas as seguintes métricas por classe:

- Precision.
- Recall.
- F1-score.
- PR-AUC, utilizando Average Precision (AP).

Também foram calculadas a acurácia geral e a matriz de confusão.

## 6. Resultados

A acurácia geral obtida foi de **98,36%**.

### Métricas por classe

| Classe | Precision | Recall | F1-score | PR-AUC (AP) | Support |
|---|---:|---:|---:|---:|---:|
| Benigno (0) | 92,99% | 98,09% | 95,47% | 99,22% | 1.149 |
| Ataque (1) | 99,59% | 98,42% | 99,00% | 99,93% | 5.386 |

A PR-AUC foi calculada por classe utilizando a abordagem um-contra-o-resto (*one-vs-rest*), com `average_precision_score`.

### Matriz de confusão

A ordem das classes é benigno (0) e ataque (1).

| Classe real / prevista | Benigno (0) | Ataque (1) |
|---|---:|---:|
| Benigno (0) | 1.127 | 22 |
| Ataque (1) | 85 | 5.301 |

Interpretação:

- Verdadeiros negativos: 1.127.
- Falsos positivos: 22.
- Falsos negativos: 85.
- Verdadeiros positivos: 5.301.

Os 85 falsos negativos representam fluxos de ataque classificados incorretamente como benignos. Esse resultado merece atenção especial em um sistema de detecção de intrusão (IDS).

## 7. Artefatos gerados

O treinamento gera os seguintes arquivos:

- `models/random_forest_baseline.joblib`: Pipeline treinado, salvo localmente para reutilização.
- `docs/metrics/random_forest_baseline.json`: arquivo com métricas, parâmetros do experimento e matriz de confusão.

O diretório `models/` está incluído no `.gitignore`, evitando que o modelo binário seja versionado automaticamente.

## 8. Como reproduzir o experimento

Com o ambiente virtual ativado e o dataset disponível na raiz do projeto, executar:

```powershell
python -m pip install -r requirements.txt
python .\scripts\treina_random_forest.py
```

O script realiza o carregamento dos dados, pré-processamento, treinamento, avaliação e salvamento dos artefatos.

## 9. Limitações e próximos passos

Apesar dos resultados positivos, existem limitações importantes:

1. A avaliação utiliza uma divisão aleatória do mesmo dataset, não dados independentes.
2. O experimento considera somente registros com `dur` preenchida.
3. O conjunto selecionado apresenta desbalanceamento entre as classes.
4. A variável `service` precisa ser avaliada em um experimento comparativo.
5. A decisão sobre a utilização de `ct_state_ttl` ainda precisa ser definida.
6. As métricas obtidas não garantem que o modelo terá o mesmo desempenho em redes reais.

Como próximos passos, recomenda-se:

- Comparar os resultados com e sem a variável `service`.
- Investigar a utilização de `ct_state_ttl`.
- Avaliar o modelo com dados independentes.
- Comparar o Random Forest com outros algoritmos.
- Analisar os falsos negativos para identificar possíveis padrões de ataques não detectados.

## 10. Conclusão

O baseline de Random Forest foi implementado utilizando um Pipeline com pré-processamento e classificação.

O modelo alcançou 98,36% de acurácia geral e 99,00% de F1-score para a classe de ataques. Na matriz de confusão, foram identificados 85 falsos negativos e 22 falsos positivos.

Esse experimento estabelece uma referência inicial para o projeto PET-IDS e permite futuras comparações entre modelos e configurações.

Entretanto, os resultados ainda precisam ser validados com dados independentes antes de considerar o modelo adequado para utilização em um ambiente real.