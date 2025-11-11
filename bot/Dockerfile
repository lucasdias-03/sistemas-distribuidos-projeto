FROM node:20-alpine

WORKDIR /app

# Instalar dependências do sistema para ZeroMQ
RUN apk add --no-cache zeromq-dev g++ make python3

# Copiar package files
COPY package*.json ./
RUN npm install

# Copiar código
COPY . .

CMD ["node", "bot.js"]