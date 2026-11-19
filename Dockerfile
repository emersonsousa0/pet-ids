# Usamos uma imagem base do Ubuntu para ter facilidade na instalação de pacotes de rede
FROM ubuntu:22.04

# Evita perguntas interativas durante a instalação dos pacotes
ENV DEBIAN_FRONTEND=noninteractive

# Atualiza o sistema e instala o tcpdump e o Suricata
RUN apt-get update && apt-get install -y \
    tcpdump \
    suricata \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Cria um diretório de trabalho para logs e regras
WORKDIR /app

# Comando padrão ao iniciar o container
CMD ["suricata", "-V"]