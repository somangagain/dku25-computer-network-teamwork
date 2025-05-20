import json, socket, threading, sys, logging, time
from datetime import datetime, timezone

if len(sys.argv) != 3: print("Usage: python server.py <server_name> <port>"); sys.exit(1)

NAME = sys.argv[1]; PORT = int(sys.argv[2])
DNS_HOST, DNS_PORT = "127.0.0.1", 4000

USERS = {"u1": "p1", "u2": "p2", "u3": "p3", "u4": "p4"}
MAILBOX = {}
INBOX = []
OUTBOX = []

lock_mailbox = threading.Lock()
lock_inbox = threading.Lock()
lock_outbox = threading.Lock()
stop_event = threading.Event()

# logging
logging.basicConfig(
    level=logging.INFO,
    format=f"[%(asctime)s] [MAIL:{NAME}] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("mail")

def gen_mail_id() -> str:
    return f"mail_{int(time.time() * 1000)}"

def dns_register() -> None:
    payload = {"type": "REGISTER", "server": NAME, "ip": "127.0.0.1", "port": PORT}
    with socket.create_connection((DNS_HOST, DNS_PORT)) as s:
        s.sendall(json.dumps(payload).encode()); s.recv(1024)
    log.info("Registered to DNS")

def dns_query(server: str):
    payload = {"type": "QUERY", "server": server}
    with socket.create_connection((DNS_HOST, DNS_PORT)) as s:
        s.sendall(json.dumps(payload).encode())
        return json.loads(s.recv(1024).decode())

def send_remote(mail, target) -> bool:
    try:
        with socket.create_connection((target["ip"], target["port"]), timeout=10) as s:
            s.sendall(json.dumps(mail).encode())
            r = s.recv(1024).decode()
        return r == 'RECEIVED'
    except Exception as e:
        log.error(f"Remote send error: {e}"); return False

def handler_client(conn, addr):
    log.info(f"Client {addr} connected"); 
    user = None
    try:
        while not stop_event.is_set():
            data = conn.recv(4096)
            if not data: break

            cmd, *args = data.decode().strip().split("::")
            cmd = cmd.upper()

            if cmd == "LOGIN":
                uid, pw = args
                if USERS.get(uid) == pw:
                    user = uid; conn.sendall(b"OK")
                else:
                    conn.sendall(b"LOGIN_FAIL")

            elif cmd == "LOGOUT":
                conn.sendall(b"BYE"); break

            elif cmd == "LIST":
                with lock_mailbox:
                    conn.sendall(json.dumps(MAILBOX.get(user, [])).encode())

            elif cmd == "READ":
                mid = args[0]
                with lock_mailbox:
                    mail = next((m for m in MAILBOX.get(user, []) if m["id"] == mid), None)
                conn.sendall(f"READ_OK::{mail}".encode() if mail else b"NOT_FOUND")

            elif cmd == "DELETE":
                mid = args[0]
                with lock_mailbox:
                    before = len(MAILBOX.get(user, []))
                    MAILBOX[user] = [m for m in MAILBOX.get(user, []) if m["id"] != mid]
                    conn.sendall(b"DELETE_OK" if len(MAILBOX[user]) < before else b"DELETE_FAIL")

            elif cmd == "SEND":
                recv_full, subj, body = args
                try:
                    r_user, r_srv = recv_full.split("@")
                except ValueError:
                    conn.sendall(b"INVALID_RECEIVER"); continue
                mail = {
                    "type": "MAIL_TRANSFER",
                    "id": gen_mail_id(),
                    "sender": f"{user}@{NAME}",
                    "receiver": r_user,
                    "subject": subj,
                    "body": body,
                    "date": datetime.now(timezone.utc).isoformat(),
                }
                if r_srv == NAME:
                    with lock_mailbox:
                        MAILBOX.setdefault(r_user, []).append(mail)
                    conn.sendall(b"SEND_OK")
                else:
                    target = dns_query(r_srv)
                    if target.get("status") != "OK":
                        conn.sendall(b"SEND_FAIL_DNS"); continue
                    conn.sendall(b"SEND_OK" if send_remote(mail, target) else b"SEND_FAIL_REMOTE")
            else:
                conn.sendall(b"INVALID_CMD")
    except Exception as e:
        log.exception(f"Client handler error: {e}")
    finally:
        conn.close(); log.info(f"Client {addr} disconnected")

def handler_remote(conn, addr):
    try:
        if conn.recv(4, socket.MSG_PEEK) == b"PING": conn.recv(4); conn.sendall(b"PONG"); conn.close(); return
        
        mail = json.loads(conn.recv(4096).decode())
        if mail.get("type") == "MAIL_TRANSFER":
            with lock_mailbox:
                MAILBOX.setdefault(mail["receiver"], []).append(mail)
            conn.sendall(b"RECEIVED")
    except Exception as e:
        log.exception(f"Remote handler error: {e}")
    finally:
        conn.close()

def process_inbox():
    pass

def process_outbox():
    pass

def process_queue():
    while not stop_event.is_set():
        process_inbox()
        process_outbox()
        time.sleep(1)

def main():
    dns_register()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0) 
    sock.bind(("0.0.0.0", PORT)); sock.listen()
    log.info(f"Mail Server Listening on 0.0.0.0:{PORT}")

    threading.Thread(target=process_queue, daemon=True).start()

    while True:
        try:
            conn, addr = sock.accept()
            peek = conn.recv(4, socket.MSG_PEEK)
            target = handler_remote if peek.startswith(b"PING") or peek[:1] == b"{" else handler_client

            threading.Thread(target=target, args=(conn, addr), daemon=True).start()
        except socket.timeout:
            continue
        except KeyboardInterrupt:
            log.info(f"Mail Server Shutting Down...")
            stop_event.set()
            sock.close()
            time.sleep(1)
            exit(0)

if __name__ == "__main__":
    main()