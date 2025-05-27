import json, socket, threading, sys, logging, time
from datetime import datetime, timezone
from queue import Queue, Empty

class MailServer:
    def __init__(self, name: str, port: int):
        self.name = name
        self.port = port
        self.dns_host, self.dns_port = "127.0.0.1", 4000
        self.users = {"u1": "p1", "u2": "p2", "u3": "p3", "u4": "p4"}
        self.mailbox: dict[str, list[dict]] = dict()
        self.inbox: Queue[dict] = Queue()
        self.outbox: Queue[tuple[dict, str, int]] = Queue()
        self.lock_mailbox = threading.Lock()
        self.stop_event = threading.Event()
        self.max_retries = 3
        self.retry_delay = 5

        logging.basicConfig(
            level=logging.INFO,
            format=f"[%(asctime)s] [MAIL:{self.name}] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.log = logging.getLogger("mail")

    def gen_mail_id(self) -> str:
        return f"mail_{int(time.time() * 1000)}"

    def dns_register(self):
        payload = {"type": "REGISTER", "server": self.name, "ip": "127.0.0.1", "port": self.port}
        with socket.create_connection((self.dns_host, self.dns_port)) as s:
            s.sendall(json.dumps(payload).encode())
            s.recv(1024)
        self.log.info("Registered to DNS")

    def dns_query(self, server: str):
        payload = {"type": "QUERY", "server": server}
        with socket.create_connection((self.dns_host, self.dns_port)) as s:
            s.sendall(json.dumps(payload).encode())
            return json.loads(s.recv(1024).decode())

    def send_remote(self, mail: dict, target: dict) -> bool:
        try:
            with socket.create_connection((target["ip"], target["port"]), timeout=10) as s:
                s.sendall(json.dumps(mail).encode())
                r = s.recv(1024).decode()
            return r == "RECEIVED"
        except Exception as e:
            self.log.error(f"Remote send error: {e}")
            return False

    def handler_client(self, conn: socket.socket, addr):
        self.log.info(f"Client {addr} connected")
        user = None
        try:
            while not self.stop_event.is_set():
                data = conn.recv(4096)
                if not data:
                    break

                cmd, *args = data.decode().strip().split("::")
                cmd = cmd.upper()

                if cmd == "LOGIN":
                    uid, pw = args
                    if self.users.get(uid) == pw:
                        user = uid
                        conn.sendall(b"OK")
                    else:
                        conn.sendall(b"LOGIN_FAIL")

                elif cmd == "LOGOUT":
                    conn.sendall(b"BYE")
                    break

                elif cmd == "LIST":
                    with self.lock_mailbox:
                        mails = self.mailbox.get(user, [])
                        summary = [
                            {k: m[k] for k in ("id", "sender", "subject", "date")}
                            for m in mails
                        ]
                    conn.sendall(json.dumps(summary).encode())

                elif cmd == "READ":
                    mid = args[0]
                    with self.lock_mailbox:
                        mail = next((m for m in self.mailbox.get(user, []) if m["id"] == mid), None)
                    conn.sendall(f"READ_OK::{mail}".encode() if mail else b"NOT_FOUND")

                elif cmd == "DELETE":
                    mid = args[0]
                    with self.lock_mailbox:
                        before = len(self.mailbox.get(user, []))
                        self.mailbox[user] = [m for m in self.mailbox.get(user, []) if m["id"] != mid]
                        conn.sendall(b"DELETE_OK" if len(self.mailbox[user]) < before else b"DELETE_FAIL")

                elif cmd == "SEND":
                    recv_full, subj, body = args
                    try:
                        r_user, r_srv = recv_full.split("@")
                    except ValueError:
                        conn.sendall(b"INVALID_RECEIVER")
                        continue

                    mail = {
                        "type": "MAIL_TRANSFER",
                        "id": self.gen_mail_id(),
                        "sender": f"{user}@{self.name}",
                        "receiver": r_user,
                        "subject": subj,
                        "body": body,
                        "date": datetime.now(timezone.utc).isoformat(),
                    }

                    if r_srv == self.name:
                        with self.lock_mailbox:
                            self.mailbox.setdefault(r_user, []).append(mail)
                        conn.sendall(b"SEND_OK")
                    else:
                        self.outbox.put((mail, r_srv, 0))
                        conn.sendall(b"SEND_QUEUED")
                else:
                    conn.sendall(b"INVALID_CMD")
        except Exception as e:
            self.log.exception(f"Client handler error: {e}")
        finally:
            conn.close()
            self.log.info(f"Client {addr} disconnected")

    def handler_remote(self, conn: socket.socket, addr):
        try:
            if conn.recv(4, socket.MSG_PEEK) == b"PING":
                conn.recv(4)
                conn.sendall(b"PONG")
                return

            mail = json.loads(conn.recv(4096).decode())
            if mail.get("type") == "MAIL_TRANSFER":
                self.inbox.put(mail)
                conn.sendall(b"RECEIVED")
        except Exception as e:
            self.log.exception(f"Remote handler error: {e}")
        finally:
            conn.close()

    def process_inbox(self):
        processed = 0
        while True:
            try:
                mail = self.inbox.get_nowait()
            except Empty:
                break
            with self.lock_mailbox:
                self.mailbox.setdefault(mail["receiver"], []).append(mail)
            self.inbox.task_done()
            processed += 1
        if processed:
            self.log.debug(f"INBOX delivered {processed} mail(s)")

    def process_outbox(self):
        requeue: list[tuple[dict, str, int]] = []
        while True:
            try:
                mail, target_srv, retries = self.outbox.get_nowait()
            except Empty:
                break
            except Exception as e:
                self.log.error(f"OUTBOX unpack error: {e}")
                continue

            try:
                target_info = self.dns_query(target_srv)
                ok = target_info.get("status") == "OK" and self.send_remote(mail, target_info)
            except Exception as e:
                self.log.error(f"DNS or send error: {e}")
                ok = False

            if ok:
                self.log.info(f"Outbox delivered {mail['id']} to {target_srv}")
            else:
                if retries + 1 < self.max_retries:
                    self.log.warning(f"Retrying mail {mail['id']} to {target_srv} (retry {retries + 1})")
                    requeue.append((mail, target_srv, retries + 1))
                else:
                    self.log.error(f"Giving up on mail {mail['id']} after {self.max_retries} attempts")
            self.outbox.task_done()

        if requeue:
            time.sleep(self.retry_delay)
            for item in requeue:
                self.outbox.put(item)

    def queue_loop(self):
        while not self.stop_event.is_set():
            self.process_inbox()
            self.process_outbox()
            time.sleep(1)

    def serve(self):
        self.dns_register()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        sock.bind(("0.0.0.0", self.port))
        sock.listen()
        self.log.info(f"Mail Server listening on 0.0.0.0:{self.port}")

        threading.Thread(target=self.queue_loop, daemon=True).start()

        while True:
            try:
                conn, addr = sock.accept()
                peek = conn.recv(4, socket.MSG_PEEK)
                target = self.handler_remote if peek.startswith(b"PING") or peek[:1] == b"{" else self.handler_client
                threading.Thread(target=target, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                self.log.info("Mail Server shutting down…")
                self.stop_event.set()
                sock.close()
                time.sleep(1)
                break

def main():
    if len(sys.argv) != 3:
        print("Usage: python server.py <server_name> <port>")
        sys.exit(1)

    name = sys.argv[1]
    port = int(sys.argv[2])
    server = MailServer(name, port)
    server.serve()

if __name__ == "__main__":
    main()
