FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema para ZeroMQ
RUN apt-get update && \
    apt-get install -y libzmq3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Criar diretório para dados
RUN mkdir -p /data

# Desabilitar buffering do Python para ver logs em tempo real
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "server.py"]