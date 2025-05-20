import socket, json, logging

DNS_HOST, DNS_PORT = "127.0.0.1", 4000

# logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [CLIENT] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("client")

def dns_list():
    with socket.create_connection((DNS_HOST, DNS_PORT)) as s:
        s.sendall(b'{"type":"LIST"}')
        return json.loads(s.recv(4096).decode())["servers"]

def dns_query(name):
    with socket.create_connection((DNS_HOST, DNS_PORT)) as s:
        s.sendall(json.dumps({"type": "QUERY", "server": name}).encode())
        return json.loads(s.recv(1024).decode())

class Client:
    def __init__(self, ip, port):
        self.sock = socket.create_connection((ip, port))
        log.info(f"Connected to {ip}:{port}")

    def cmd(self, line):
        self.sock.sendall(line.encode())
        return self.sock.recv(4096).decode()

    def run(self):
        uid = input("ID: "); pw = input("PW: ")
        if self.cmd(f"LOGIN::{uid}::{pw}") != "OK":
            print("Login fail"); return
        
        while True:
            try:
                print("\n1 List 2 Read 3 Delete 4 Send 5 Quit")
                ch = input("> ")
                if ch == '1':
                    print(self.cmd("LIST"))
                elif ch == '2':
                    mid = input("Mail ID: "); print(self.cmd(f"READ::{mid}"))
                elif ch == '3':
                    mid = input("Mail ID: "); print(self.cmd(f"DELETE::{mid}"))
                elif ch == '4':
                    to = input("to(user@server): "); sb = input("subj: "); body = input("body: ")
                    print(self.cmd(f"SEND::{to}::{sb}::{body}"))
                elif ch == '5':
                    print(self.cmd("LOGOUT")); break
                else:
                    print("Invalid.")
            except KeyboardInterrupt:
                break
        
        self.sock.close()

if __name__ == "__main__":
    servers = dns_list()
    if not servers: print("No server registered."); exit()
    
    for i, server_id in enumerate(servers, 1): print(f"{i}. {server_id} ({servers[server_id]['ip']}:{servers[server_id]['port']})")
    sel = int(input("select server> ")) - 1
    
    name = list(servers.keys())[sel]
    info = dns_query(name)
    
    Client(info["ip"], info["port"]).run()