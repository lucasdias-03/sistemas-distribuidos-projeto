FROM golang:1.21-alpine AS builder

WORKDIR /app

# Instalar dependências do sistema necessárias para ZeroMQ
RUN apk add --no-cache gcc musl-dev zeromq-dev pkgconfig

# Copiar arquivos de dependências
COPY go.mod ./

# Copiar código fonte
COPY . .

# Baixar dependências e compilar
RUN go mod tidy && go build -o proxy .

# Imagem final
FROM alpine:latest

RUN apk add --no-cache zeromq

WORKDIR /app

COPY --from=builder /app/proxy .

EXPOSE 5557 5558

CMD ["./proxy"]