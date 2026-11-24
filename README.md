# PET IDS — Detecção Inteligente de Ameaças

## Sobre o projeto

Este repositório reúne o desenvolvimento de um projeto de detecção inteligente de ameaças, realizado no âmbito do Programa de Educação Tutorial (PET).

A proposta é estudar e desenvolver soluções voltadas à identificação de possíveis ameaças, utilizando técnicas de análise de dados e inteligência artificial.

## Objetivos

- Investigar métodos de detecção inteligente de ameaças.
- Organizar os experimentos e o desenvolvimento do projeto.
- Desenvolver e avaliar soluções de detecção.
- Promover a colaboração e o versionamento do código.

## Organização do repositório

O projeto utiliza Git e GitHub para controle de versão e colaboração entre os integrantes.

As contribuições devem seguir as orientações descritas no arquivo `CONTRIBUTING.md`.

Principais diretórios e arquivos:

| Caminho | Descrição |
|---|---|
| `scripts/` | Scripts de treinamento e experimentação. |
| `docs/contracts/` | Contratos e definições das variáveis utilizadas. |
| `docs/decisions/` | Registros de decisões técnicas. |
| `docs/experimentos/` | Relatórios dos experimentos realizados. |
| `docs/metrics/` | Resultados e métricas dos modelos. |
| `models/` | Armazenamento local dos modelos treinados. |
| `requirements.txt` | Dependências Python do projeto. |
| `CONTRIBUTING.md` | Orientações para contribuição. |

## Tecnologias

- Python
- Pandas
- NumPy
- Scikit-learn
- Joblib
- Git e GitHub

## Experimento: Baseline de Random Forest

O projeto possui um experimento inicial de classificação utilizando Random Forest para identificar fluxos de rede benignos e fluxos associados a ataques.

O modelo utiliza um `Pipeline` do Scikit-learn, integrando o pré-processamento dos dados e o treinamento do classificador.

### Dataset

O experimento utiliza o arquivo `Dataset_resumido.csv`, considerando somente os registros que possuem duração (`dur`) preenchida.

A variável `Label` representa as classes:

- `0`: tráfego benigno.
- `1`: tráfego de ataque.

O conjunto utilizado contém 32.672 registros, divididos em:

- 26.137 registros para treinamento.
- 6.535 registros para teste.

O dataset deve estar disponível na raiz do projeto e não é versionado no GitHub.

### Pré-processamento

O Pipeline realiza:

- Preenchimento de valores ausentes nas variáveis numéricas pela mediana.
- Preenchimento de valores ausentes nas variáveis categóricas pelo valor mais frequente.
- Codificação das variáveis categóricas com `OneHotEncoder`.
- Treinamento do classificador `RandomForestClassifier`.

A configuração principal utiliza 200 árvores, `class_weight="balanced"` e `random_state=42`.

### Como executar

Crie um ambiente virtual Python:

```powershell
python -m venv .venv
```

Ative o ambiente no Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```powershell
python -m pip install -r requirements.txt
```

Disponibilize o arquivo `Dataset_resumido.csv` na raiz do projeto e execute:

```powershell
python .\scripts\treina_random_forest.py
```

Ao final, o script gera o modelo treinado e o arquivo com as métricas.

### Resultados

Resultados obtidos no conjunto de teste:

| Métrica | Resultado |
|---|---:|
| Acurácia | 98,36% |
| Precision — benigno | 92,99% |
| Recall — benigno | 98,09% |
| F1-score — benigno | 95,47% |
| PR-AUC — benigno | 99,22% |
| Precision — ataque | 99,59% |
| Recall — ataque | 98,42% |
| F1-score — ataque | 99,00% |
| PR-AUC — ataque | 99,93% |
| Falsos positivos | 22 |
| Falsos negativos | 85 |

Os resultados completos, incluindo a matriz de confusão, estão disponíveis em:

- `docs/metrics/random_forest_baseline.json`
- `docs/experimentos/baseline-random-forest.md`

### Artefatos gerados

O treinamento produz:

- `models/random_forest_baseline.joblib`: Pipeline treinado, salvo localmente para reutilização.
- `docs/metrics/random_forest_baseline.json`: métricas, parâmetros e matriz de confusão.

O diretório `models/` está incluído no `.gitignore`, portanto o modelo binário não é enviado automaticamente ao GitHub.

**Observação:** os resultados representam um baseline experimental. A avaliação utiliza uma divisão aleatória do mesmo conjunto de dados e ainda precisa ser complementada com testes em dados independentes antes de qualquer aplicação em ambiente real.

## Ambiente de desenvolvimento

Pré-requisitos: Git e Docker (Docker Desktop no Windows, com Compose v2 recente).

Linux, macOS, WSL ou Git Bash com make:

```bash
make up
```

Windows (PowerShell) sem make:

```powershell
git config core.hooksPath .githooks
docker compose up -d --wait
```

Para conferir, `docker compose ps` deve mostrar PostgreSQL e Redis como `healthy`.

Outros comandos: `make down` (parar), `make reset` (parar e apagar os dados), `make logs` e `make lint`.

Os valores padrão (usuário, senha e portas) ficam no `docker-compose.yml`. Para alterá-los, copie `.env.example` para `.env`.

O hook de pre-commit executa o Ruff dentro de um container e exige o Docker em execução. Para corrigir problemas apontados: `docker compose run --rm tools check --fix .` e `docker compose run --rm tools format .`.

## Contribuição

As alterações devem ser realizadas em branches separadas e submetidas por Pull Requests, seguindo as regras de revisão e aprovação configuradas no repositório.

As orientações para contribuir estão disponíveis em `CONTRIBUTING.md`.

## Equipe

Projeto desenvolvido pelos integrantes do PET, sob orientação do professor responsável.