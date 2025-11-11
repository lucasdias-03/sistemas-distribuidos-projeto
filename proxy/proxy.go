package main

import (
	"log"

	zmq "github.com/pebbe/zmq4"
)

func main() {
	log.Println("Iniciando Proxy Pub/Sub...")

	// Socket XSUB para publishers (servidores)
	xsub, err := zmq.NewSocket(zmq.XSUB)
	if err != nil {
		log.Fatal("Erro ao criar socket XSUB:", err)
	}
	defer xsub.Close()

	err = xsub.Bind("tcp://*:5557")
	if err != nil {
		log.Fatal("Erro ao fazer bind no XSUB:", err)
	}
	log.Println("XSUB escutando na porta 5557 (publishers/servidores)")

	// Socket XPUB para subscribers (clientes/bots)
	xpub, err := zmq.NewSocket(zmq.XPUB)
	if err != nil {
		log.Fatal("Erro ao criar socket XPUB:", err)
	}
	defer xpub.Close()

	err = xpub.Bind("tcp://*:5558")
	if err != nil {
		log.Fatal("Erro ao fazer bind no XPUB:", err)
	}
	log.Println("XPUB escutando na porta 5558 (subscribers/clientes)")

	// Iniciar proxy - repassa mensagens entre publishers e subscribers
	log.Println("Proxy Pub/Sub rodando...")
	err = zmq.Proxy(xsub, xpub, nil)
	if err != nil {
		log.Fatal("Erro no proxy:", err)
	}
}