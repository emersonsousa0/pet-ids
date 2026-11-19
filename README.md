# PET IDS — Detecção Inteligente de Ameaças

## Sobre o projeto

Este repositório reúne o desenvolvimento de um projeto de detecção inteligente de ameaças, realizado no âmbito do Programa de Educação Tutorial (PET).

A proposta é estudar e desenvolver soluções voltadas à identificação de possíveis ameaças, utilizando técnicas de análise e inteligência artificial.

## Objetivos

- Investigar métodos de detecção inteligente de ameaças.
- Organizar os experimentos e o desenvolvimento do projeto.
- Desenvolver e avaliar soluções de detecção.
- Promover a colaboração e o versionamento do código.

## Organização do repositório

O projeto utiliza Git e GitHub para controle de versão e colaboração entre os integrantes.

As contribuições devem seguir as orientações descritas no arquivo [CONTRIBUTING.md](CONTRIBUTING.md).

## Tecnologias

As linguagens, ferramentas e tecnologias utilizadas serão documentadas após a definição da equipe.

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

## Equipe

Projeto desenvolvido pelos integrantes do PET, sob orientação do professor responsável.
