import socket, json, logging, threading, time
from datetime import datetime, timezone
from typing import Dict, Any

HOST, PORT          = "0.0.0.0", 4000

PING_INTERVAL       = 10
PING_TIMEOUT        = 3
PING_MAX_STRIKES    = 3

registry: Dict[str, Dict[str, Any]] = {}

lock_registry = threading.Lock()
stop_event = threading.Event()

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [DNS] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("dns")

def ping(ip: str, port: int) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=PING_TIMEOUT) as s:
            s.sendall(b"PING")
            s.settimeout(PING_TIMEOUT)
            return s.recv(4) == b"PONG"
    except Exception:
        return False

def ping_loop() -> None:
    while not stop_event.is_set():
        time.sleep(PING_INTERVAL)
        with lock_registry:
            names = list(registry.keys())
            
        for name in names:
            with lock_registry:
                info = registry.get(name)
                if not info: continue

                ip, port = info["ip"], info["port"]
                prev = info["status"]

            ok = ping(ip, port)
            new = "OK" if ok else "FAIL"

            with lock_registry:
                info = registry.get(name)
                if not info: continue

                info["status"] = new
                info["last_ping"] = datetime.now(timezone.utc).isoformat()
                info["strikes"] = 0 if new == "OK" else info.get("strikes", 0) + 1

                if new != prev: log.warning(f"Status Changed: <{name}> {prev} → {new}")

                if PING_MAX_STRIKES and info["strikes"] >= PING_MAX_STRIKES:
                    log.error(f'Removed: <{name}> after {info["strikes"]} failed pings')
                    registry.pop(name)

def handle(conn: socket.socket, addr) -> None:
    try:
        while not stop_event.is_set():
            raw = conn.recv(4096)
            if not raw: return
            
            req = json.loads(raw.decode())
            typ = req.get("type", "").upper()

            if typ == "REGISTER":
                name = req["server"]
                with lock_registry:
                    registry[name] = {
                        "ip": req["ip"],
                        "port": req["port"],
                        "status": "OK",
                        "last_seen": datetime.now(timezone.utc).isoformat(),
                        "last_ping": None,
                        "strikes": 0,
                    }
                conn.sendall(b'"REGISTERED"')
                log.info(f'Registered <{name}> → {req["ip"]}:{req["port"]}')
            elif typ == "QUERY":
                with lock_registry:
                    res = registry.get(req["server"], {"status": "FAIL"})
                conn.sendall(json.dumps(res).encode())
            elif typ == "LIST":
                with lock_registry:
                    payload = {"servers": {name: info for name, info in registry.items() if info.get("status") == "OK"}}
                conn.sendall(json.dumps(payload).encode())
            else:
                conn.sendall(b'"INVALID_REQUEST"')
    except Exception as e:
        log.exception(f"Handler error: {e}")
        try:
            conn.sendall(b'"ERROR"')
        except Exception:
            pass
    finally:
        conn.close()

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0) 
    sock.bind((HOST, PORT)); sock.listen(); 
    log.info(f"DNS listening on {HOST}:{PORT}")

    threading.Thread(target=ping_loop, daemon=True).start()

    while True:
        try:
            conn, addr = sock.accept()
            threading.Thread(target=handle, args=(conn, addr), daemon=True).start()
        except socket.timeout:
            continue
        except KeyboardInterrupt:
            log.info(f"DNS Shutting Down...")
            stop_event.set()
            sock.close()
            time.sleep(1)
            exit(0)

if __name__ == "__main__":
    main()