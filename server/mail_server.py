import socket
import threading
import json
import time
from collections import deque

# ========== 사용자 데이터 ==========
USERS = {
    "alice": "pass1",
    "bob": "pass2"
}

# ========== 메일 객체 ==========
class Mail:
    def __init__(self, sender, receiver, subject, body):
        self.sender = sender
        self.receiver = receiver
        self.subject = subject
        self.body = body
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        return {
            "from": self.sender,
            "subject": self.subject,
            "body": self.body,
            "timestamp": self.timestamp
        }

# ========== Inbox ==========
class Inboxes:
    def __init__(self):
        self.data = {user: deque() for user in USERS}

    def list_mails(self, user):
        return [f"{i}. {m.subject} ({m.timestamp})" for i, m in enumerate(self.data[user])]

    def read_mail(self, user, index):
        try:
            return self.data[user][index].to_dict()
        except IndexError:
            return None

    def delete_mail(self, user, index):
        try:
            self.data[user].remove(self.data[user][index])
            return True
        except IndexError:
            return False

# ========== Outbox ==========
class Outbox:
    def __init__(self):
        self.queue = deque()

    def enqueue(self, mail):
        self.queue.append(mail)

    def process(self, inboxes, connected_clients):
        while self.queue:
            mail = self.queue.popleft()
            receiver = mail.receiver
            if receiver in connected_clients:
                try:
                    conn = connected_clients[receiver]
                    conn.send(json.dumps({
                        "status": "new_mail",
                        "mail": mail.to_dict()
                    }).encode())
                    print(f"[Outbox] Delivered live to {receiver}")
                except Exception as e:
                    print(f"[Outbox] Live delivery failed: {e}")
                    inboxes[receiver].append(mail)
            elif receiver in inboxes.data:
                inboxes.data[receiver].append(mail)
                print(f"[Outbox] Stored to inbox: {receiver}")
            else:
                print(f"[Outbox] Unknown receiver: {receiver}")

# ========== 전역 ==========
inboxes = Inboxes()
outbox = Outbox()
connected_clients = {}  # user_id -> conn

# ========== 클라이언트 처리 ==========
def handle_client(conn):
    user = None
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break

            print(f"[DEBUG] Received data: {data.decode()}") 

            request = json.loads(data.decode())
            cmd = request.get("cmd")

            if cmd == "login":
                uid = request["id"]
                pw = request["pw"]

                print(f"[DEBUG] Login attempt: {uid} / {pw}")

                if uid not in USERS:
                    conn.send(json.dumps({"status": "ID_unknown"}).encode())
                elif USERS[uid] != pw:
                    conn.send(json.dumps({"status": "PASSWORD_wrong"}).encode())
                else:
                    user = uid
                    connected_clients[user] = conn
                    conn.send(json.dumps({"status": "OK"}).encode())

            elif cmd == "send":
                if not user:
                    conn.send(json.dumps({"status": "not_logged_in"}).encode())
                    continue
                mail = Mail(
                    sender=user,
                    receiver=request["to"],
                    subject=request["subject"],
                    body=request["body"]
                )
                outbox.enqueue(mail)
                conn.send(json.dumps({"status": "queued"}).encode())

            elif cmd == "list":
                if not user:
                    conn.send(json.dumps({"status": "not_logged_in"}).encode())
                    continue
                mails = inboxes.list_mails(user)
                if not mails:
                    conn.send(json.dumps({"status": "empty"}).encode())
                else:
                    conn.send(json.dumps({"status": "OK", "mails": mails}).encode())

            elif cmd == "read":
                if not user:
                    conn.send(json.dumps({"status": "not_logged_in"}).encode())
                    continue
                index = request["index"]
                content = inboxes.read_mail(user, index)
                if content:
                    conn.send(json.dumps({"status": "OK", "mail": content}).encode())
                else:
                    conn.send(json.dumps({"status": "not_found"}).encode())

            elif cmd == "delete":
                if not user:
                    conn.send(json.dumps({"status": "not_logged_in"}).encode())
                    continue
                index = request["index"]
                success = inboxes.delete_mail(user, index)
                conn.send(json.dumps({"status": "deleted" if success else "not_found"}).encode())

    finally:
        if user:
            connected_clients.pop(user, None)
        conn.close()

# ========== Outbox 처리 스레드 ==========
def process_outbox_loop():
    while True:
        outbox.process(inboxes, connected_clients)
        time.sleep(5)

# ========== 서버 실행 ==========
def start_server():
    threading.Thread(target=process_outbox_loop, daemon=True).start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', 9001))
    server.listen()
    print("[Server] Listening on port 9001...")

    while True:
        conn, _ = server.accept()
        threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    start_server()