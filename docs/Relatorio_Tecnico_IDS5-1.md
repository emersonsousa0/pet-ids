# Relatório Técnico --- IDS 5

## Detecção de ameaças em redes com análise de datasets e eventos do Suricata

**Projeto:** IDS 5\
**Entregável:** Relatório técnico em Markdown\
**Finalidade:** Documentar a análise dos datasets e a implementação
complementar de coleta e transformação de eventos do Suricata.

------------------------------------------------------------------------

## 1. Objetivo

Este documento registra duas frentes de trabalho:

1.  A análise exploratória das versões completa e resumida do dataset
    publicado no Kaggle.
2.  Uma implementação complementar com Suricata para observar eventos de
    rede, testar uma regra de detecção e transformar registros do
    `eve.json` em arquivos CSV.

É importante separar a implementação complementar descrita neste
relatório do experimento original apresentado no artigo do grupo. A
instalação realizada durante esta atividade não deve ser interpretada
como reprodução idêntica do ambiente original dos autores.

## 2. Fontes e materiais utilizados

-   Artigo do grupo: **"Construção de Datasets Controlados e Análise
    Preditiva de Ameaças Cibernéticas via Aprendizado Supervisionado"**.
-   Dataset no Kaggle: [Network Threat Detection
    Dataset](https://www.kaggle.com/datasets/rebsonramalho/network-threat-detection-dataset).
-   Arquivos analisados: `Dataset_completo.csv` e
    `Dataset_resumido.csv`.
-   Logs gerados na implementação complementar:
    `/var/log/suricata/eve.json`.
-   Script de transformação: `transformar_suricata.py`.

## 3. Análise exploratória dos datasets

A análise exploratória foi realizada no Google Colab. Foram examinados o
tamanho dos arquivos, a distribuição da variável-alvo (`Label`), a
presença de valores ausentes, registros duplicados e os nomes das
colunas.

### 3.1 Comparação geral

  Indicador                          Dataset completo   Dataset resumido
  -------------------------------- ------------------ ------------------
  Registros                                   368.017             55.826
  Colunas                                          29                 25
  Valores ausentes                                  0            476.931
  Percentual de valores ausentes                0,00%             34,17%
  Linhas duplicadas                             5.572              5.572
  Percentual de duplicatas                      1,51%              9,98%

Os percentuais de duplicatas foram calculados em relação à quantidade de
registros de cada arquivo. A contagem representa linhas duplicadas
identificadas pela análise realizada.

### 3.2 Distribuição das classes

A variável `Label` representa a classe utilizada na classificação.

**Dataset completo**

  Classe (`Label`)       Registros   Percentual
  ------------------ ------------- ------------
  0                         31.282        8,50%
  1                        336.735       91,50%
  **Total**            **368.017**     **100%**

O dataset completo apresenta forte predominância da classe 1.

**Dataset resumido**

  Classe (`Label`)      Registros   Percentual
  ------------------ ------------ ------------
  0                        26.280       47,07%
  1                        29.546       52,93%
  **Total**            **55.826**     **100%**

No dataset resumido, a distribuição entre as duas classes é mais
equilibrada.

> A interpretação semântica exata de cada valor de `Label` deve seguir a
> documentação oficial do dataset. Neste relatório, os valores são
> apresentados como classes 0 e 1, sem atribuir nomes adicionais que não
> tenham sido confirmados pela documentação.

### 3.3 Valores ausentes e duplicatas

O dataset completo não apresentou valores ausentes na leitura realizada.
Foram identificadas 5.572 linhas duplicadas, correspondentes a
aproximadamente 1,51% dos registros.

O dataset resumido apresentou 476.931 células ausentes, equivalentes a
aproximadamente 34,17% do total de células. Também foram identificadas
5.572 linhas duplicadas, aproximadamente 9,98% dos registros.

Esses resultados devem ser considerados em qualquer etapa posterior de
preparação dos dados. A decisão de remover duplicatas, preencher valores
ausentes ou manter registros deve ser documentada e justificada, pois
pode alterar a distribuição e o comportamento dos dados.

### 3.4 Dicionário de dados

O notebook de análise exploratória (`.ipynb`) contém o dicionário de
dados das colunas dos dois arquivos. Abaixo estão os nomes exatos das
colunas identificadas em cada versão.

**Dataset completo --- 29 colunas**

    Nº Coluna
  ---- -------------------
     1 `srcip`
     2 `sport`
     3 `dstip`
     4 `dsport`
     5 `proto`
     6 `state`
     7 `dur`
     8 `sbytes`
     9 `dbytes`
    10 `sttl`
    11 `service`
    12 `Sload`
    13 `Dload`
    14 `Spkts`
    15 `Dpkts`
    16 `swin`
    17 `stcpb`
    18 `dtcpb`
    19 `smeansz`
    20 `dmeansz`
    21 `trans_depth`
    22 `res_bdy_len`
    23 `Stime`
    24 `Ltime`
    25 `synack`
    26 `ackdat`
    27 `is_sm_ips_ports`
    28 `ct_state_ttl`
    29 `Label`

**Dataset resumido --- 25 colunas**

    Nº Coluna
  ---- -------------------
     1 `srcip`
     2 `sport`
     3 `dstip`
     4 `dsport`
     5 `proto`
     6 `state`
     7 `dur`
     8 `sbytes`
     9 `dbytes`
    10 `service`
    11 `Sload`
    12 `Dload`
    13 `Spkts`
    14 `Dpkts`
    15 `smeansz`
    16 `dmeansz`
    17 `trans_depth`
    18 `res_bdy_len`
    19 `Stime`
    20 `Ltime`
    21 `synack`
    22 `ackdat`
    23 `is_sm_ips_ports`
    24 `ct_state_ttl`
    25 `Label`

**Observação sobre o dicionário:** as descrições semânticas apresentadas
no notebook são interpretações preliminares baseadas nos nomes das
variáveis e no contexto de tráfego de rede. Elas devem ser tratadas como
descrições inferidas, não como um dicionário oficial fornecido pelos
autores, a menos que sejam confirmadas pela documentação original do
dataset.

## 4. Contexto do processo original descrito no artigo

Segundo o artigo do grupo, o ambiente experimental original utilizou:

-   Ubuntu 24.04.2 LTS como host sensor.
-   Kali Linux 2025.2 como máquina atacante.
-   Metasploitable como máquina de destino.
-   Suricata em modo passivo, monitorando uma rede Host-Only
    `192.168.56.x`.
-   Uma rede Bridge `10.0.0.x` para acesso externo e atualizações, não
    utilizada como rede monitorada.
-   Geração de eventos pelo Suricata no arquivo `eve.json`.
-   ELK para indexação e visualização dos eventos.
-   Capturas paralelas com `tcpdump` e `tshark`.

O artigo descreve duas versões do dataset: uma completa, que combina
registros do Suricata com capturas do `tcpdump`, e uma resumida, baseada
exclusivamente em logs do Suricata. Também descreve extração separada,
sincronização temporal e unificação por meio de um script Python.

O artigo não apresenta todos os detalhes necessários para reconstruir
exatamente a execução original, como a versão exata do Suricata, o
arquivo integral de configuração, a lista exata de tipos EVE habilitados
e utilizados, o script original e o mapeamento documentado de cada
atributo para sua fonte.

## 5. Implementação complementar do Suricata

### 5.1 Ambiente utilizado

Foi criada uma máquina virtual Ubuntu 24.04 no VirtualBox, utilizando a
interface de rede `enp0s3`.

Informações observadas no ambiente complementar:

  Item                      Informação
  ------------------------- ------------------------------------------
  Sistema operacional       Ubuntu 24.04
  Ferramenta                Suricata
  Versão instalada          8.0.3 RELEASE
  Interface monitorada      `enp0s3`
  Endereço IPv4 observado   `10.0.2.15/24`
  Arquivo de eventos        `/var/log/suricata/eve.json`
  Arquivo de regras         `/var/lib/suricata/rules/suricata.rules`

A interface `enp0s3` foi configurada no bloco `af-packet` do arquivo
`/etc/suricata/suricata.yaml`, substituindo a referência inicial a
`eth0`, que não existia nessa máquina virtual.

A rede utilizada nesta implementação foi a rede NAT padrão do VirtualBox
(`10.0.2.0/24`). Portanto, ela é diferente da topologia Host-Only
`192.168.56.x` descrita para o experimento original no artigo.

### 5.2 Regras e teste de detecção

As regras Emerging Threats Open foram obtidas por meio do comando
`suricata-update`. A saída do processo informou o carregamento de 69.557
regras, com 53.582 habilitadas e 15 desabilitadas.

Também foi adicionada uma regra local de teste para identificar
requisições ICMP Echo Request:

``` text
alert icmp any any -> any any (msg:"Teste de alerta Suricata"; itype:8; sid:1000001; rev:1;)
```

A configuração foi validada com:

``` bash
sudo suricata -T -c /etc/suricata/suricata.yaml
```

O teste de tráfego foi realizado com:

``` bash
ping -c 4 8.8.8.8
```

Foram observados quatro pacotes de teste e eventos de alerta
correspondentes à assinatura `Teste de alerta Suricata`, com
`signature_id` 1000001 e severidade 3. O campo `action` apresentou o
valor `allowed`, indicando que o tráfego foi permitido; o teste
comprovou a geração do alerta, não o bloqueio do tráfego.

### 5.3 Configuração EVE e tipos de eventos

O arquivo `/etc/suricata/suricata.yaml` foi consultado para verificar a
configuração de saída EVE. A saída estava habilitada, com gravação em
arquivo regular chamado `eve.json`.

Na execução observada, foram contabilizados os seguintes tipos de
eventos:

  Tipo de evento (`event_type`)     Quantidade
  ------------------------------- ------------
  `alert`                                  124
  `dns`                                    118
  `fileinfo`                                 3
  `flow`                                   231
  `http`                                   124
  `quic`                                    11
  `stats`                                  156
  `tls`                                     22
  **Total**                            **789**

Essas quantidades representam os eventos encontrados no arquivo
`eve.json` analisado durante a implementação complementar. Não
representam necessariamente a quantidade de eventos do experimento
original nem a quantidade de ataques únicos.

O script contabiliza todos os tipos de eventos encontrados, mas exporta
registros detalhados apenas dos tipos `flow` e `alert`. Os demais tipos
aparecem no arquivo de resumo.

## 6. Transformação dos eventos EVE em CSV

Foi desenvolvido o script `transformar_suricata.py`, utilizando
bibliotecas padrão do Python (`json`, `csv`, `pathlib` e `collections`).
O script lê o arquivo `eve.json`, percorre os eventos JSON linha a
linha, contabiliza os tipos de evento e separa os registros de fluxo e
de alerta.

O processamento gera três arquivos:

  Arquivo de saída         Conteúdo
  ------------------------ -----------------------------------------
  `fluxos_suricata.csv`    Campos selecionados dos eventos `flow`
  `alertas_suricata.csv`   Campos selecionados dos eventos `alert`
  `resumo_eventos.csv`     Quantidade de eventos por tipo

O script foi executado com:

``` bash
sudo python3 transformar_suricata.py
```

Resultado informado pela execução:

``` text
Arquivo criado: /home/vboxuser/fluxos_suricata.csv
Arquivo criado: /home/vboxuser/alertas_suricata.csv
Arquivo criado: /home/vboxuser/resumo_eventos.csv

===== RESULTADO DA TRANSFORMAÇÃO =====
Fluxos encontrados: 231
Alertas encontrados: 124
Tipos de eventos: 8
Transformação concluída!
```

### 6.1 Colunas provenientes dos eventos `flow`

O arquivo `fluxos_suricata.csv` contém os campos abaixo. A origem indica
o objeto do evento EVE do qual cada campo é extraído.

  Coluna no CSV      Origem no evento EVE
  ------------------ ---------------------------
  `timestamp`        Campo principal do evento
  `flow_id`          Campo principal do evento
  `in_iface`         Campo principal do evento
  `src_ip`           Campo principal do evento
  `src_port`         Campo principal do evento
  `dest_ip`          Campo principal do evento
  `dest_port`        Campo principal do evento
  `proto`            Campo principal do evento
  `ip_v`             Campo principal do evento
  `pkts_toserver`    Objeto `flow`
  `pkts_toclient`    Objeto `flow`
  `bytes_toserver`   Objeto `flow`
  `bytes_toclient`   Objeto `flow`
  `start`            Objeto `flow`
  `end`              Objeto `flow`
  `age`              Objeto `flow`
  `state`            Objeto `flow`
  `reason`           Objeto `flow`
  `alerted`          Objeto `flow`
  `tcp_flags`        Objeto `tcp`

### 6.2 Colunas provenientes dos eventos `alert`

O arquivo `alertas_suricata.csv` contém os campos abaixo.

  Coluna no CSV    Origem no evento EVE
  ---------------- ---------------------------
  `timestamp`      Campo principal do evento
  `flow_id`        Campo principal do evento
  `in_iface`       Campo principal do evento
  `src_ip`         Campo principal do evento
  `src_port`       Campo principal do evento
  `dest_ip`        Campo principal do evento
  `dest_port`      Campo principal do evento
  `proto`          Campo principal do evento
  `ip_v`           Campo principal do evento
  `icmp_type`      Campo principal do evento
  `icmp_code`      Campo principal do evento
  `direction`      Campo principal do evento
  `action`         Objeto `alert`
  `gid`            Objeto `alert`
  `signature_id`   Objeto `alert`
  `rev`            Objeto `alert`
  `signature`      Objeto `alert`
  `category`       Objeto `alert`
  `severity`       Objeto `alert`

Campos como portas, categoria ou outros atributos podem ficar vazios
quando não estão presentes no evento de origem. Por exemplo, os
registros ICMP de teste não possuem portas TCP/UDP; por isso `src_port`
e `dest_port` aparecem vazios no CSV. Isso é esperado e não significa,
por si só, erro na transformação.

### 6.3 Resumo dos arquivos gerados

A transformação gerou 231 registros de fluxo, 124 registros de alerta e
um resumo contendo oito tipos de eventos. Os três arquivos foram
inspecionados para conferir cabeçalhos e amostras de registros.

O script mantém fluxos e alertas em arquivos separados. Ele não realiza
a sincronização temporal e a unificação dos dados do Suricata com
capturas do `tcpdump` descritas no processo original do artigo.
Portanto, esta etapa é uma extração complementar e não uma reprodução
integral do pipeline original de geração do dataset.

## 7. Limitações e cuidados de interpretação

1.  A versão 8.0.3 do Suricata corresponde à implementação complementar
    realizada nesta atividade. A versão usada no experimento original
    não foi identificada no artigo.
2.  A configuração da máquina virtual complementar utiliza `enp0s3` e
    rede NAT `10.0.2.0/24`, enquanto o artigo descreve uma topologia
    Host-Only `192.168.56.x` para monitoramento.
3.  Os oito tipos e suas quantidades correspondem ao arquivo EVE
    produzido na execução complementar.
4.  O script desenvolvido extrai `flow` e `alert` para CSVs separados e
    contabiliza todos os tipos de eventos; não reproduz a sincronização
    com `tcpdump` nem a unificação descrita no artigo.
5.  O artigo informa que não foi documentada uma auditoria atributo por
    atributo dos campos usados no treinamento. Recomenda-se avaliar
    identificadores de rede e possíveis características específicas da
    topologia para evitar vazamento de informação no treinamento e na
    avaliação dos modelos.
6.  As descrições semânticas das colunas do dataset devem ser conferidas
    com a documentação oficial. O notebook apresenta um dicionário
    preliminar baseado nos nomes e no contexto das variáveis.

## 8. Conclusão

A atividade reuniu a análise exploratória das versões completa e
resumida do dataset e uma implementação complementar de coleta e
transformação de eventos do Suricata. A análise identificou diferenças
relevantes entre as versões dos dados, especialmente na quantidade de
registros, distribuição das classes, presença de valores ausentes e
proporção de duplicatas.

Na implementação complementar, o Suricata 8.0.3 foi configurado para
monitorar a interface de rede da máquina virtual, gerar eventos EVE e
registrar alertas de uma regra ICMP de teste. O script Python separou os
eventos de fluxo e alerta em arquivos CSV e produziu um resumo dos tipos
de eventos observados.

Para revisão e reprodução, os entregáveis relacionados devem ser
mantidos no repositório: notebook `.ipynb`, este relatório `.md`, script
`transformar_suricata.py` e os arquivos CSV gerados. O PDF pode ser
mantido como versão complementar do relatório em Markdown.

## 9. Referências e artefatos

-   Artigo do grupo: *Construção de Datasets Controlados e Análise
    Preditiva de Ameaças Cibernéticas via Aprendizado Supervisionado*.
-   Kaggle: [Network Threat Detection
    Dataset](https://www.kaggle.com/datasets/rebsonramalho/network-threat-detection-dataset).
-   Documentação oficial do Suricata: <https://docs.suricata.io/>.
-   Atualizador de regras: <https://suricata-update.readthedocs.io/>.

**Arquivos complementares esperados no repositório:**

-   Notebook de análise exploratória (`.ipynb`).
-   Relatório técnico (`.md` --- este documento).
-   Script de transformação (`transformar_suricata.py`).
-   `fluxos_suricata.csv`.
-   `alertas_suricata.csv`.
-   `resumo_eventos.csv`.
-   PDF do relatório, se desejado, como versão complementar.
