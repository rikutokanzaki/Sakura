package main

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"time"

	"gossh/internal/auth"
	"gossh/internal/connector"
	"gossh/internal/handler"
	"gossh/internal/logger"
	"gossh/internal/resource"

	"golang.org/x/crypto/ssh"
)

const (
	host = "0.0.0.0"
	port = 22
)

func main() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	privateKey, err := loadOrGenerateHostKey("/certs/ssh_host_rsa_key")
	if err != nil {
		log.Fatalf("Failed to load host key: %v", err)
	}

	listener, err := net.Listen("tcp", fmt.Sprintf("%s:%d", host, port))
	if err != nil {
		log.Fatalf("Failed to listen on %s:%d: %v", host, port, err)
	}
	defer listener.Close()

	log.Printf("SSH Proxy listening on %s:%d", host, port)

	for {
		tcpConn, err := listener.Accept()
		if err != nil {
			log.Printf("Failed to accept connection: %v", err)
			continue
		}

		go handleClient(tcpConn, privateKey)
	}
}

func handleClient(tcpConn net.Conn, hostKey ssh.Signer) {
	defer func() {
		if r := recover(); r != nil {
			log.Printf("Recovered from panic in handleClient: %v", r)
		}
	}()

	addr := tcpConn.RemoteAddr().String()
	log.Printf("Connection from %s", addr)

	authenticator := auth.NewAuthenticator("./config/user.txt")
	heraldingConnector := connector.NewSSHConnector("heralding", 22)
	cowrieConnector := connector.NewSSHConnector("cowrie", 2222)

	var username, password string
	var cowrieLaunched bool

	config := &ssh.ServerConfig{
		NoClientAuth: false,
		PasswordCallback: func(conn ssh.ConnMetadata, pass []byte) (*ssh.Permissions, error) {
			username = conn.User()
			password = string(pass)

			go func() {
				defer func() {
					if r := recover(); r != nil {
						log.Printf("Recovered from panic in record_login: %v", r)
					}
				}()
				_ = heraldingConnector.RecordLogin(username, password)
			}()

			authSuccess := authenticator.Authenticate(username, password)
			logger.LogAuthEvent(addr, fmt.Sprintf("%s:%d", host, port), username, password, authSuccess)

			if authSuccess {
				go triggerCowrie(&cowrieLaunched)
				return nil, nil
			}
			return nil, fmt.Errorf("authentication failed")
		},
	}

	config.AddHostKey(hostKey)

	sshConn, chans, reqs, err := ssh.NewServerConn(tcpConn, config)
	if err != nil {
		if err != io.EOF {
			log.Printf("SSH handshake failed: %v", err)
		}
		resource.CloseSocket(tcpConn)
		return
	}

	go ssh.DiscardRequests(reqs)

	for newChannel := range chans {
		if newChannel.ChannelType() != "session" {
			newChannel.Reject(ssh.UnknownChannelType, "unknown channel type")
			continue
		}

		channel, requests, err := newChannel.Accept()
		if err != nil {
			log.Printf("Failed to accept channel: %v", err)
			continue
		}

		go func(ch ssh.Channel, reqs <-chan *ssh.Request) {
			defer func() {
				if r := recover(); r != nil {
					log.Printf("Recovered from panic in session handler: %v", r)
				}
				resource.CloseChannel(ch)
			}()

			for req := range reqs {
				switch req.Type {
				case "pty-req":
					req.Reply(true, nil)
				case "shell":
					req.Reply(true, nil)
					startTime := time.Now()
					handler.HandleSession(ch, username, password, addr, startTime, cowrieLaunched, cowrieConnector, sshConn, tcpConn)
					return
				case "exec":
					req.Reply(true, nil)
				default:
					if req.WantReply {
						req.Reply(false, nil)
					}
				}
			}
		}(channel, requests)
	}

	resource.CloseConnection(sshConn)
	resource.CloseSocket(tcpConn)
}

func triggerCowrie(launched *bool) {
	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Post("http://launcher:5000/trigger/cowrie", "application/json", nil)
	if err != nil {
		log.Printf("Error triggering cowrie at auth: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 {
		log.Printf("Cowrie started in auth stage")
		*launched = true
	} else {
		log.Printf("Failed to start cowrie at auth (HTTP %d)", resp.StatusCode)
	}
}

func loadOrGenerateHostKey(keyPath string) (ssh.Signer, error) {
	keyBytes, err := os.ReadFile(keyPath)
	if err != nil {
		privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
		if err != nil {
			return nil, err
		}

		privateKeyPEM := &pem.Block{
			Type:  "RSA PRIVATE KEY",
			Bytes: x509.MarshalPKCS1PrivateKey(privateKey),
		}

		keyFile, err := os.Create(keyPath)
		if err != nil {
			return nil, err
		}
		defer keyFile.Close()

		if err := pem.Encode(keyFile, privateKeyPEM); err != nil {
			return nil, err
		}

		keyBytes = pem.EncodeToMemory(privateKeyPEM)
	}

	return ssh.ParsePrivateKey(keyBytes)
}
