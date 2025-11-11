FROM golang:1.21-alpine AS builder

WORKDIR /app

# Instalar dependências do sistema necessárias para ZeroMQ
RUN apk add --no-cache gcc musl-dev zeromq-dev pkgconfig

# Copiar arquivos de dependências e código fonte
COPY go.mod ./
COPY . .
RUN go mod tidy

# Compilar
RUN go build -o broker .

# Imagem final
FROM alpine:latest

RUN apk add --no-cache zeromq

WORKDIR /app

COPY --from=builder /app/broker .

EXPOSE 5555

CMD ["./broker"]