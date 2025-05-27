import socket
import json
import logging
import sys

DNS_HOST, DNS_PORT = "127.0.0.1", 4000

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [CLIENT] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("client")


def dns_list() -> dict:
    with socket.create_connection((DNS_HOST, DNS_PORT)) as s:
        s.sendall(b'{"type": "LIST"}')
        return json.loads(s.recv(4096).decode())["servers"]


def dns_query(name: str) -> dict:
    with socket.create_connection((DNS_HOST, DNS_PORT)) as s:
        payload = {"type": "QUERY", "server": name}
        s.sendall(json.dumps(payload).encode())
        return json.loads(s.recv(1024).decode())


class Client:
    def __init__(self, ip: str, port: int):
        self.sock = socket.create_connection((ip, port))
        log.info(f"Connected to server at {ip}:{port}")

    def cmd(self, line: str) -> str:
        self.sock.sendall(line.encode())
        return self.sock.recv(4096).decode()

    def run(self):
        try:
            uid = input("ID: ")
            pw = input("PW: ")
            if self.cmd(f"LOGIN::{uid}::{pw}") != "OK":
                print("Login failed.")
                return

            while True:
                print("\n1 List  2 Read  3 Delete  4 Send  5 Quit")
                choice = input("> ").strip()

                if choice == "1":
                    response = self.cmd("LIST")
                    try:
                        mails = json.loads(response)
                        for m in mails:
                            print(f"- [{m['id']}] From: {m['sender']} | Subj: {m['subject']} | Date: {m['date']}")
                    except json.JSONDecodeError:
                        print("Invalid LIST response:", response)

                elif choice == "2":
                    mid = input("Mail ID: ")
                    print(self.cmd(f"READ::{mid}"))

                elif choice == "3":
                    mid = input("Mail ID: ")
                    print(self.cmd(f"DELETE::{mid}"))

                elif choice == "4":
                    to = input("To (user@server): ")
                    subj = input("Subject: ")
                    body = input("Body: ")
                    print(self.cmd(f"SEND::{to}::{subj}::{body}"))

                elif choice == "5":
                    print(self.cmd("LOGOUT"))
                    break

                else:
                    print("Invalid option.")

        except KeyboardInterrupt:
            print("\nDisconnected.")
        except Exception as e:
            log.exception(f"Unexpected error: {e}")
        finally:
            self.sock.close()
            log.info("Connection closed")


def main():
    servers = dns_list()
    if not servers:
        print("No mail server registered.")
        return

    print("\nAvailable Mail Servers:")
    for idx, name in enumerate(servers, 1):
        info = servers[name]
        print(f"{idx}. {name} ({info['ip']}:{info['port']})")

    try:
        sel = int(input("Select server> ")) - 1
        name = list(servers.keys())[sel]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    info = dns_query(name)
    if info.get("status") != "OK":
        print(f"Server {name} not found.")
        return

    client = Client(info["ip"], info["port"])
    client.run()


if __name__ == "__main__":
    main()
