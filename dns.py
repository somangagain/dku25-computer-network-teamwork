import socket
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any


class DNSRegistryServer:
    def __init__(self, host="0.0.0.0", port=4000):
        self.host = host
        self.port = port
        self.registry: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.sock = None

        self.PING_INTERVAL = 10
        self.PING_TIMEOUT = 3
        self.PING_MAX_STRIKES = 3

        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] [DNS] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.log = logging.getLogger("dns")

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(1.0)
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        self.log.info(f"DNS listening on {self.host}:{self.port}")

        threading.Thread(target=self.ping_loop, daemon=True).start()

        while not self.stop_event.is_set():
            try:
                conn, addr = self.sock.accept()
                threading.Thread(target=self.handle_connection, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                self.log.info("DNS Shutting Down...")
                self.stop_event.set()
                self.sock.close()
                break

    def ping_loop(self):
        while not self.stop_event.is_set():
            time.sleep(self.PING_INTERVAL)
            with self.lock:
                names = list(self.registry.keys())

            for name in names:
                with self.lock:
                    info = self.registry.get(name)
                    if not info:
                        continue
                    ip, port = info["ip"], info["port"]
                    prev_status = info["status"]

                ok = self.ping(ip, port)
                new_status = "OK" if ok else "FAIL"

                with self.lock:
                    info = self.registry.get(name)
                    if not info:
                        continue
                    info["status"] = new_status
                    info["last_ping"] = datetime.now(timezone.utc).isoformat()
                    info["strikes"] = 0 if new_status == "OK" else info.get("strikes", 0) + 1

                    if new_status != prev_status:
                        self.log.warning(f"Status Changed: <{name}> {prev_status} → {new_status}")

                    if self.PING_MAX_STRIKES and info["strikes"] >= self.PING_MAX_STRIKES:
                        self.log.error(f"Removed: <{name}> after {info['strikes']} failed pings")
                        self.registry.pop(name)

    def ping(self, ip: str, port: int) -> bool:
        try:
            with socket.create_connection((ip, port), timeout=self.PING_TIMEOUT) as s:
                s.sendall(b"PING")
                s.settimeout(self.PING_TIMEOUT)
                return s.recv(4) == b"PONG"
        except Exception:
            return False

    def handle_connection(self, conn: socket.socket, addr):
        try:
            while not self.stop_event.is_set():
                raw = conn.recv(4096)
                if not raw:
                    return

                try:
                    req = json.loads(raw.decode())
                except json.JSONDecodeError:
                    conn.sendall(b'"INVALID_JSON"')
                    return

                typ = req.get("type", "").upper()

                if typ == "REGISTER":
                    name = req["server"]
                    with self.lock:
                        self.registry[name] = {
                            "ip": req["ip"],
                            "port": req["port"],
                            "status": "OK",
                            "last_seen": datetime.now(timezone.utc).isoformat(),
                            "last_ping": None,
                            "strikes": 0,
                        }
                    conn.sendall(b'"REGISTERED"')
                    self.log.info(f"Registered <{name}> → {req['ip']}:{req['port']}")

                elif typ == "QUERY":
                    with self.lock:
                        res = self.registry.get(req["server"], {"status": "FAIL"})
                    conn.sendall(json.dumps(res).encode())

                elif typ == "LIST":
                    with self.lock:
                        payload = {
                            "servers": {
                                name: info
                                for name, info in self.registry.items()
                                if info.get("status") == "OK"
                            }
                        }
                    conn.sendall(json.dumps(payload).encode())

                else:
                    conn.sendall(b'"INVALID_REQUEST"')

        except Exception as e:
            self.log.exception(f"Handler error: {e}")
            try:
                conn.sendall(b'"ERROR"')
            except Exception:
                pass
        finally:
            conn.close()


if __name__ == "__main__":
    DNSRegistryServer().start()
