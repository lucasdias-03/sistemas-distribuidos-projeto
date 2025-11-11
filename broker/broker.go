package main

import (
	"log"

	zmq "github.com/pebbe/zmq4"
)

func main() {
	log.Println("Iniciando Broker...")

	// Socket ROUTER para clientes (frontend)
	frontend, err := zmq.NewSocket(zmq.ROUTER)
	if err != nil {
		log.Fatal("Erro ao criar socket frontend:", err)
	}
	defer frontend.Close()

	err = frontend.Bind("tcp://*:5555")
	if err != nil {
		log.Fatal("Erro ao fazer bind no frontend:", err)
	}
	log.Println("Frontend (ROUTER) escutando na porta 5555")

	// Socket DEALER para servidores (backend)
	backend, err := zmq.NewSocket(zmq.DEALER)
	if err != nil {
		log.Fatal("Erro ao criar socket backend:", err)
	}
	defer backend.Close()

	err = backend.Bind("tcp://*:5556")
	if err != nil {
		log.Fatal("Erro ao fazer bind no backend:", err)
	}
	log.Println("Backend (DEALER) escutando na porta 5556")

	// Iniciar proxy (queue device) - faz round-robin automaticamente
	log.Println("Broker rodando - fazendo proxy entre clientes e servidores...")
	err = zmq.Proxy(frontend, backend, nil)
	if err != nil {
		log.Fatal("Erro no proxy:", err)
	}
}