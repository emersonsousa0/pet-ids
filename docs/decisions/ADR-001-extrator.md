# ADR-001: Extrator de features (treino e tráfego ao vivo)

- **Status:** Rascunho (hipótese, não aceita)
- **Data:** 15/11/2026
- **Atualizado em:** 15/11/2026 (segunda passada)
- **Responsável:** (seu nome)
- **Task:** IDS 7
- **Depende de:** IDS 5 (estudo do dataset e do processo de geração). Sem a resposta da IDS 5
  sobre a origem dos blocos e do rótulo, esta ADR **não pode** passar de Rascunho.
- **Evidências:** `docs/inspecao_dataset.json`, `docs/verificacao_numeros_chave.json`,
  `scripts/inspeciona_dataset.py`, `scripts/verifica_numeros_chave.py`

## Contexto

O modelo de ML é treinado com o dataset do grupo parceiro
(kaggle.com/datasets/rebsonramalho/network-threat-detection-dataset). A descrição do
Kaggle informa que `Label` é binário: **1 = ataque, 0 = benigno** (368.017 registros =
336.735 ataque + 31.282 benigno; resumido 55.826 = 29.546 + 26.280). O dataset **não**
traz tipo/categoria de ataque — portanto não permite análise por tipo de ataque.

O ambiente de geração informado tem **dois sensores**: Suricata produzindo `eve.json`
e captura de pacotes com **tcpdump/tshark**; scripts Python fizeram o **merge temporal**
das duas fontes. A inspeção mostrou que o dataset **não é homogêneo**: ele concatena
registros com estruturas e distribuições diferentes. Reproduzir "as 29 colunas" com um
único pipeline pode ser impossível sem antes decidir qual parte do dataset é a referência.

> **Hipótese (não fato):** o bloco C (proto numérico, 1 pacote por linha) viria da
> **captura de pacotes**, não do `eve.json`. O bloco B teria forma de `flow` do Suricata.
> Isso ainda precisa ser confirmado pelo grupo/IDS 5.

## O que foi medido

| Arquivo | Linhas | Colunas | Label=1 (ataque) | Label=0 (benigno) |
|---|---:|---:|---:|---:|
| `Dataset_completo.csv` | 368.017 | 29 | 336.735 (91,5%) | 31.282 (8,5%) |
| `Dataset_resumido.csv` | 55.826 | 25 | 29.546 (52,9%) | 26.280 (47,1%) |

Esses totais foram **conferidos por um caminho independente** (sem pandas) e batem
exatamente.

O completo se divide em três blocos com assinaturas distintas:

| Bloco | Critério observado | Linhas | % | Label=1 | Perfil |
|---|---|---:|---:|---:|---|
| A | proto com nome + `Stime='0'` | 22.957 | 6,2% | 10,6% | HTTP sem métricas de fluxo; 21.126 linhas com método/URL em `trans_depth`/`res_bdy_len` |
| B | proto com nome + `Stime` preenchido | 32.869 | 8,9% | 82,5% | fluxo real: `dur`, bytes e pacotes preenchidos; timestamps ISO-8601 |
| C | proto numérico (6, 17, 1, 2) | 312.191 | 84,8% | 98,4% | `Spkts=1`, `Dpkts=0`, `dur=0`, `state=0`, só 33.975 5-tuplas únicas |

> O bloco C é **hipótese de origem** (captura de pacotes/tshark), não fato. A alta
> proporção de `Label=1` em C (98,4%) pode ser consequência de o bloco capturar
> predominantemente ataques — não de o rótulo descrever cada fluxo individualmente.

O `Dataset_resumido` é exatamente **A+B** (as 55.826 linhas com proto nomeado), na mesma
ordem, sem as colunas `sttl`, `swin`, `stcpb` e `dtcpb` e com as ausências representadas
por vazio em vez de `0` (não é uma troca mecânica de todo `0` por vazio: zeros reais são
preservados). Ele **não** é amostra aleatória nem agregação.

## Evidência a favor do Suricata

- `service` usa o vocabulário de `app_proto` do Suricata: `http`, `dns`, `tls`, `ftp`,
  `ssh`, `smb`, `rfb`, `smtp`, `telnet`, `dhcp`, `ntp`, `failed`.
- `state` usa `new`, `closed`, `established` — subconjunto dos valores de `flow.state`
  do Suricata (que também emite `bypassed`).
- As linhas com `GET`/`POST`/`OPTIONS` em `trans_depth` e URL em `res_bdy_len` têm a forma
  de um evento `http` do eve.json.
- Os timestamps ISO-8601 estão no formato de `datetime` do Python com fuso (`+00:00`),
  consistente com uma transformação de `flow.start`/`flow.end`.

## Evidência contra (ou que falta explicar)

- **84,8% das linhas têm `proto` numérico** (6/17/1/2), enquanto o eve.json usa `proto`
  textual (`"TCP"`, `"UDP"`). Esse bloco C também tem 1 pacote por linha. Ele não parece
  saída direta do Suricata; a **hipótese** é que venha da captura de pacotes
  (tcpdump/tshark), unida ao eve.json por um merge temporal em Python.
- `sttl`, `swin`, `stcpb` e `dtcpb` são **zero em 100% dos blocos A e B** e só têm valores
  no bloco C.
- `synack` e `ackdat` são booleanos (`0`/`True`/`False`), não tempos em segundos.
- `ct_state_ttl` contém nomes de estado TCP, não uma contagem por faixa de TTL.
- **O rótulo está confundido com o bloco.** `Label=1` é 10,6% em A, 82,5% em B e 98,4% em
  C. Não há como separar "aprendeu o ataque" de "aprendeu qual sensor/bloco gerou a linha".
- **Rede:** os CSVs usam `192.168.56.x` (Host-Only). Não há **nenhum** IP `10.0.0.x`
  (Bridge), mas há 305 ocorrências de `10.0.3.x` (`10.0.3.15` e `10.0.3.3`) que precisam
  de explicação.
- O zip `dataset-pet.zip` contém **apenas os dois CSVs** — não há README, dicionário de
  colunas, script de transformação nem `eve.json` de exemplo.
- Não há PCAP nem `eve.json` **anexados ao dataset** para validar o mapeamento.

## Decisão (hipótese)

Manter o **Suricata** como extrator principal do tráfego ao vivo, na mesma versão,
configuração e conjunto de regras do dataset, **desde que** o grupo parceiro confirme que
os blocos A/B vêm do `eve.json` e explique o bloco C. NFStream e CICFlowMeter continuam
descartados para reproduzir o treino: eles não produzem `app_proto`/`flow.state` do
Suricata nem as colunas derivadas com estas unidades.

**Recomendação provisória (proposta, depende de decisão do time):** usar o
`Dataset_resumido.csv` (blocos **A+B**, 55.826 linhas) como **referência inicial do
extrator Suricata**, em vez do completo. Motivos: (i) remove o bloco C, cuja origem é
hipotética e cujo perfil `dur=0`/`Spkts=1` não corresponde a um fluxo; (ii) remove as
quatro colunas que só existem em C (`sttl`, `swin`, `stcpb`, `dtcpb`); (iii) mantém o
bloco B, que tem a forma de `flow` do eve.json. A proposta **não** é decisão fechada
enquanto o time/IDS 5 não confirmar qual dataset é canônico.

> A decisão não vira definitiva enquanto não existir um PCAP de teste que, passando pelo
> pipeline do grupo e pelo nosso, produza as mesmas linhas/colunas. Também depende da
> **IDS 5** para explicar a geração do dataset e do rótulo.

## Consequências e riscos concretos

1. **Treinar no completo aprende o bloco C, não necessariamente o ataque.** 84,8% das
   linhas têm `dur=0`, `state=0`, `Spkts=1`, `Dpkts=0` e 98,4% `Label=1`. Um modelo pode
   separar as classes memorizando o bloco (ou o par `dur=0`/`Label`), com desempenho alto
   que não se transfere para tráfego ao vivo. Como a origem do bloco C é **hipótese**,
   treinar nele é apostar em uma fonte que ainda não foi confirmada.
2. **Rótulo binário, mas de origem desconhecida.** A descrição do Kaggle confirma
   `1 = ataque` e `0 = benigno`; porém **não** diz como o rótulo foi produzido (alerta do
   Suricata, cenário de ataque ou marcação manual). Ele está **confundido com o bloco**:
   10,6% / 82,5% / 98,4% de `Label=1` em A/B/C. Tratar esse rótulo como verdade pode
   gerar vazamento. Além disso, só há classe binária: **não é possível analisar tipo de
   ataque** com este dataset.
3. **Duas colunas HTTP estão quebradas.** `trans_depth` e `res_bdy_len` contêm método e
   URL em 21.233 linhas; não há nenhum valor numérico > 0. Se o extrator ao vivo emitir
   inteiros, o modelo recebe um tipo/distribuição que nunca viu.
4. **Unidade de carga diferente do UNSW.** `Sload`/`Dload` são **bytes/s** (medido:
   `Sload == sbytes/dur` em 100% das linhas com `dur>0`), não bits/s. Implementar a fórmula
   medida, não a do UNSW.
5. **`dur=0` em 91,2% das linhas** e `Ltime == Stime` nas 312.191 linhas do bloco epoch.
   Um extrator ao vivo que calcule duração real produz distribuição diferente.
6. **Oito colunas não são reproduzíveis só com o `eve.json`**: `sttl`, `swin`, `stcpb`,
   `dtcpb`, `synack`, `ackdat`, `trans_depth`, `ct_state_ttl`. Mantê-las no treino cria
   features que o ao vivo não terá (ou terá com outro significado).
7. **Codificação de `proto` inconsistente.** O completo mistura nomes e códigos; o
   Suricata emite nomes. É preciso normalizar antes de treinar, senão 84,8% das linhas
   viram categorias inexistentes no ao vivo.
8. **Timestamps em dois formatos** (epoch e ISO-8601) na mesma coluna, com `Stime='0'` em
   22.957 linhas. Definir epoch em segundos como formato canônico.
9. **Transformação com bugs.** 4 linhas têm múltiplos valores no mesmo campo
   (`srcip='a,b'`, `sttl='64,52'`, `proto='1,17'`); 5.572 linhas são duplicatas exatas.
   Esses defeitos precisam ser reproduzidos ou corrigidos no script do grupo — não
   improvisados no nosso.
10. **Dependência de regras e versão.** Features de alerta mudam com o ruleset. Fixar
    versão e configuração no Docker.
11. **Desempenho na VPS.** Confirmar que o Suricata roda em tempo real no ambiente da IDS 4.
12. **Escolha do dataset canônico.** Treinar no completo e no resumido dá modelos
    diferentes. É preciso decidir (com o grupo) qual é a referência e registrar no contrato.

## Colunas não reproduzíveis (e por quê)

> "Não reproduzível" aqui significa **não reproduzível só com o `eve.json`**. O ambiente
> também tem captura de pacotes (tcpdump/tshark); parte destas colunas pode ser derivada
> do PCAP e precisa ser confirmada.

| Coluna | Classificação | Motivo | Alternativa |
|---|---|---|---|
| `sttl` | `indisponivel_no_eve` | `flow` do eve.json não expõe TTL | PCAP/tshark (TODO confirmar) |
| `swin` | `indisponivel_no_eve` | não há janela TCP no `flow`; o objeto `tcp` traz flags/estado | PCAP/tshark (TODO confirmar) |
| `stcpb` | `nao_reproduzivel` | não há seq base no `flow`; os valores do dataset (0/1/449…) não parecem seq; unidade desconhecida | PCAP/tshark (TODO confirmar) |
| `dtcpb` | `nao_reproduzivel` | idem; 94,4% das linhas têm `stcpb == dtcpb` | PCAP/tshark (TODO confirmar) |
| `synack` | `nao_reproduzivel` | é intervalo SYN→SYN-ACK; no dataset virou booleano | timestamps de pacote (TODO confirmar) |
| `ackdat` | `nao_reproduzivel` | é intervalo SYN-ACK→ACK; no dataset virou booleano | timestamps de pacote (TODO confirmar) |
| `trans_depth` | `nao_reproduzivel` | Suricata não expõe profundidade de transação; a coluna tem o método HTTP | remover / TODO confirmar |
| `ct_state_ttl` | `nao_reproduzivel` | a coluna tem estado TCP detalhado, não contagem por TTL | remover / TODO confirmar |

## Diferença entre completo e resumido

- **Relação:** o resumido é subconjunto linha a linha do completo (mesma ordem),
  restrito às linhas com `proto` nomeado (A+B): 55.826 = 22.957 + 32.869.
- **Colunas:** o resumido perde `sttl`, `swin`, `stcpb`, `dtcpb` (todas zero em A/B).
  As 25 restantes mantêm nome e ordem.
- **Nulos:** o resumido preserva ausência como vazio; o completo preencheu com `0`/`0.0`.
  Não há regra única de conversão: `dbytes` tem 41.182 zeros no completo, mas só 22.957
  vazios no resumido (os demais zeros são reais).
- **Rótulo:** 91,5% de `Label=1` no completo contra 52,9% no resumido (1=ataque, 0=benigno;
  totais conferem com a descrição do Kaggle).
- **Conclusão:** o resumido é a parte "limpa" (A+B) e é a **recomendação provisória** como
  referência do extrator Suricata, mas ainda contém o bloco A sem métricas de fluxo e as
  colunas HTTP quebradas. Nenhum dos dois está pronto para treino sem limpeza e sem
  confirmação do grupo.

## Plano de mitigação

- **Proposta (depende do time):** adotar `Dataset_resumido` (A+B) como referência inicial
  do extrator Suricata; não usar o completo sem separar/remover o bloco C.
- Separar os blocos explicitamente (campo `bloco_presente` no contrato) para não misturar
  features ausentes em A com features de fluxo de B.
- Remover do treino as 8 colunas não reproduzíveis só com `eve.json` (ou reproduzi-las via
  tcpdump/tshark, se confirmado) e `is_sm_ips_ports` (constante 0).
- Implementar as unidades medidas: `dur` em s, `Sload`/`Dload` em bytes/s.
- Normalizar `proto`, `state`, `service` e timestamps para um formato único.
- Obter do grupo PCAP + `eve.json` + script do merge e fazer um teste de paridade: mesmo
  PCAP nos dois pipelines, comparar coluna a coluna (tipo, unidade, distribuição).
- Fixar versão do Suricata e do ruleset no ambiente.
- **Aguardar a IDS 5** para confirmar a origem do bloco C e do rótulo antes de fechar a
  escolha do dataset canônico.

## Próximos passos

- [x] Inspecionar os dois CSVs e registrar tipos, unidades e problemas
- [x] Preencher o contrato v0 com as medições
- [x] Verificar os números-chave por um caminho independente
- [ ] Receber PCAP, `eve.json` de exemplo e o script de transformação/merge
- [ ] Confirmar a origem do bloco C e como `Label` foi gerado (depende da IDS 5)
- [ ] Decidir qual dataset é canônico e quais colunas saem do treino
- [ ] Fazer o teste de paridade com um PCAP
- [ ] Mudar o status para **Aceito** e abrir o pull request
