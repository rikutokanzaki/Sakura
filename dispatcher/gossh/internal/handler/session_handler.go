package handler

import (
	"encoding/binary"
	"fmt"
	"gossh/internal/connector"
	"gossh/internal/logger"
	"gossh/internal/reader"
	"gossh/internal/resource"
	"gossh/internal/utils"
	"log"
	"net"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"golang.org/x/crypto/ssh"
)

const (
	updateSessionURL = "http://launcher:5000/session/update/cowrie"
	updateInterval   = 1500 * time.Millisecond
)

var (
	updateLock   sync.Mutex
	lastUpdateAt time.Time
	httpClient   = &http.Client{Timeout: 2 * time.Second}
)

func updateSession(force bool) {
	now := time.Now()

	if !force && now.Sub(lastUpdateAt) < updateInterval {
		return
	}

	updateLock.Lock()
	defer updateLock.Unlock()

	now = time.Now()
	if !force && now.Sub(lastUpdateAt) < updateInterval {
		return
	}

	lastUpdateAt = now

	go func() {
		_, err := httpClient.Post(updateSessionURL, "application/json", nil)
		if err != nil {
			log.Printf("Session update failed: %v", err)
		}
	}()
}

func buildDirCmd(cwd string) string {
	if cwd == "" || cwd == "~" {
		return ""
	}
	return fmt.Sprintf("cd %s", cwd)
}

func HandleSession(
	channel ssh.Channel,
	requests <-chan *ssh.Request,
	username, password, addr string,
	startTime time.Time,
	cowrieLaunched bool,
	cowrieConnector *connector.SSHConnector,
	sshConn ssh.Conn,
	tcpConn net.Conn,
) {
	history := []string{}
	cwd := "~"

	hostname := os.Getenv("HOST_NAME")
	if len(hostname) > 9 {
		hostname = hostname[:9]
	}

	termWidth := cowrieConnector.GetTerminalWidth()
	termHeight := cowrieConnector.GetTerminalHeight()

	go func() {
		for req := range requests {
			switch req.Type {
			case "window-change":
				width, height := parseWindowChange(req.Payload)
				termWidth = int(width)
				termHeight = int(height)
				cowrieConnector.UpdateTerminalSize(termWidth, termHeight)
				if req.WantReply {
					req.Reply(true, nil)
				}
			default:
				if req.WantReply {
					req.Reply(false, nil)
				}
			}
		}
	}()

	prompt := utils.GetPrompt(username, hostname, cwd)
	lineReader := reader.NewLineReader(channel, username, password, prompt, history, cowrieConnector)

	channel.Write([]byte("\r\n"))

	motdLines := utils.GetMotdLines(hostname)
	for _, line := range motdLines {
		sentLine := strings.TrimRight(line, "\n") + "\r\n"
		channel.Write([]byte(sentLine))
		time.Sleep(5 * time.Millisecond)
	}

	if cowrieLaunched {
		updateSession(true)
	}

	defer func() {
		if r := recover(); r != nil {
			log.Printf("Recovered from panic in session: %v", r)
		}

		duration := time.Since(startTime)
		srcIP, srcPort := parseAddr(addr)
		logger.LogSessionClose(srcIP, srcPort, username, duration, "Session closed")

		lineReader.CleanupTerminal()
		resource.CloseChannel(channel)
		resource.CloseConnection(sshConn)
		resource.CloseSocket(tcpConn)
	}()

	for {
		cmd := lineReader.Read()

		if cmd == "" {
			continue
		}

		srcIP, srcPort := parseAddr(addr)
		logger.LogCommandEvent(srcIP, srcPort, username, cmd, cwd)

		cmdLower := strings.ToLower(strings.TrimRight(cmd, ";"))
		if cmdLower == "exit" || cmdLower == "quit" {
			break
		}

		if !cowrieLaunched {
			history = append(history, cmd)

			client := &http.Client{Timeout: 5 * time.Second}
			resp, err := client.Post("http://launcher:5000/trigger/cowrie", "application/json", nil)
			if err != nil {
				log.Printf("Error triggering Cowrie: %v", err)
				channel.Write([]byte("Service unavailable. Session terminated.\r\n"))
				break
			}

			if resp.StatusCode == 200 {
				log.Printf("Cowrie started. Transferring session...")
				resp.Body.Close()
			} else {
				log.Printf("Failed to start Cowrie (HTTP %d)", resp.StatusCode)
				resp.Body.Close()
				channel.Write([]byte("Service unavailable. Session terminated.\r\n"))
				break
			}

			cowrieLaunched = true

			output, newCwd, err := cowrieConnector.ReplayHistory(username, password, history)
			if err != nil {
				log.Printf("Cowrie connection failed during replay_history: %v", err)
				channel.Write([]byte("Connection to backend lost. Session terminated.\r\n"))
				break
			}

			cwd = newCwd
			prompt = utils.GetPrompt(username, hostname, cwd)
			lineReader.UpdatePrompt(prompt)

			channel.Write([]byte(output))
			updateSession(true)
			continue
		}

		dirCmd := buildDirCmd(cwd)

		output, newCwd, err := cowrieConnector.ExecuteCommand(cmd, username, password, dirCmd)
		if err != nil {
			log.Printf("Cowrie connection lost during command execution: %v", err)
			channel.Write([]byte("Connection to backend lost. Session terminated.\r\n"))
			break
		}

		cwd = newCwd
		prompt = utils.GetPrompt(username, hostname, cwd)
		lineReader.UpdatePrompt(prompt)

		channel.Write([]byte(output))
		updateSession(false)
	}
}

func parseWindowChange(payload []byte) (width, height uint32) {
	if len(payload) < 8 {
		return 80, 24
	}
	width = binary.BigEndian.Uint32(payload[0:4])
	height = binary.BigEndian.Uint32(payload[4:8])
	return
}

func parseAddr(addr string) (string, int) {
	parts := strings.Split(addr, ":")
	if len(parts) >= 2 {
		var port int
		fmt.Sscanf(parts[len(parts)-1], "%d", &port)
		ip := strings.Join(parts[:len(parts)-1], ":")
		return ip, port
	}
	return addr, 0
}
