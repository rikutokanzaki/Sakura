package resource

import (
	"log"
	"net"

	"golang.org/x/crypto/ssh"
)

func CloseChannel(channel ssh.Channel) {
	if channel == nil {
		return
	}

	defer func() {
		if r := recover(); r != nil {
			log.Printf("Panic while closing channel: %v", r)
		}
	}()

	channel.SendRequest("exit-status", false, ssh.Marshal(struct{ Status uint32 }{0}))
	channel.Close()
}

func CloseConnection(conn ssh.Conn) {
	if conn == nil {
		return
	}

	defer func() {
		if r := recover(); r != nil {
			log.Printf("Panic while closing connection: %v", r)
		}
	}()

	conn.Close()
}

func CloseSocket(conn net.Conn) {
	if conn == nil {
		return
	}

	defer func() {
		if r := recover(); r != nil {
			log.Printf("Panic while closing socket: %v", r)
		}
	}()

	conn.Close()
}

type sshSessionCloser interface {
	Close() error
}

func CloseSSHSession(client *ssh.Client, session sshSessionCloser) {
	if session != nil {
		session.Close()
	}

	if client != nil {
		client.Close()
	}
}
