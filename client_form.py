import tkinter as tk
from tkinter import messagebox, scrolledtext
import socket
import json


DNS_HOST, DNS_PORT = "127.0.0.1", 4000


def dns_list():
    with socket.create_connection((DNS_HOST, DNS_PORT)) as s:
        s.sendall(b'{"type":"LIST"}')
        return json.loads(s.recv(4096).decode())["servers"]


def dns_query(name):
    with socket.create_connection((DNS_HOST, DNS_PORT)) as s:
        s.sendall(json.dumps({"type": "QUERY", "server": name}).encode())
        return json.loads(s.recv(1024).decode())


class MailClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Potato Mail")
        self.geometry("700x500")

        self.sock = None
        self.username = None
        self.mailbox = []

        self.frames = {}

        self.build_frames()
        self.show_frame("ServerSelect")

    def build_frames(self):
        self.frames["ServerSelect"] = self.build_server_select_frame()
        self.frames["Login"] = self.build_login_frame()
        self.frames["Main"] = self.build_main_frame()

    def show_frame(self, name):
        for frame in self.frames.values():
            frame.pack_forget()
        self.frames[name].pack(fill="both", expand=True)

    def build_server_select_frame(self):
        frame = tk.Frame(self)
        tk.Label(frame, text="Select Mail Server", font=("Arial", 16)).pack(pady=10)

        self.server_listbox = tk.Listbox(frame, width=50)
        self.server_listbox.pack(pady=10)

        tk.Button(frame, text="Refresh", command=self.refresh_server_list).pack(pady=5)
        tk.Button(frame, text="Connect", command=self.select_server).pack()

        return frame

    def refresh_server_list(self):
        self.servers = dns_list()
        self.server_listbox.delete(0, tk.END)
        for i, name in enumerate(self.servers):
            info = self.servers[name]
            self.server_listbox.insert(i, f"{name} ({info['ip']}:{info['port']})")

    def select_server(self):
        try:
            idx = self.server_listbox.curselection()[0]
            self.server_name = list(self.servers.keys())[idx]
            info = dns_query(self.server_name)
            self.sock = socket.create_connection((info["ip"], info["port"]))
            self.show_frame("Login")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {e}")

    def build_login_frame(self):
        frame = tk.Frame(self)

        tk.Label(frame, text="Login", font=("Arial", 16)).pack(pady=10)

        self.entry_id = tk.Entry(frame, width=30)
        self.entry_pw = tk.Entry(frame, width=30, show="*")
        self.label_login_info = tk.Label(frame, text="", fg="red")

        tk.Label(frame, text="User ID").pack()
        self.entry_id.pack(pady=2)
        tk.Label(frame, text="Password").pack()
        self.entry_pw.pack(pady=2)

        tk.Button(frame, text="Login", command=self.login).pack(pady=10)
        self.label_login_info.pack()

        return frame

    def login(self):
        uid = self.entry_id.get()
        pw = self.entry_pw.get()
        try:
            self.sock.sendall(f"LOGIN::{uid}::{pw}".encode())
            res = self.sock.recv(1024).decode()
            if res == "OK":
                self.username = uid
                self.label_login_info.config(text="Login Success", fg="green")
                self.show_frame("Main")
                self.load_mail_list()
            else:
                self.label_login_info.config(text="Login Failed", fg="red")
        except Exception as e:
            self.label_login_info.config(text=f"Error: {e}", fg="red")

    def build_main_frame(self):
        frame = tk.Frame(self)

        # Top buttons
        tk.Frame(frame).pack()
        btn_frame = tk.Frame(frame)
        tk.Button(btn_frame, text="Inbox", command=self.load_mail_list).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Logout", command=self.logout).pack(side="left", padx=5)
        btn_frame.pack(pady=10)

        # Mail list
        tk.Label(frame, text="Inbox", font=("Arial", 14)).pack(pady=5)
        self.mail_listbox = tk.Listbox(frame, width=100, height=10)
        self.mail_listbox.pack(padx=10, pady=5)
        self.mail_listbox.bind("<<ListboxSelect>>", self.read_selected_mail)

        # Compose
        tk.Label(frame, text="Compose Mail", font=("Arial", 14)).pack(pady=5)

        self.entry_to = tk.Entry(frame, width=70)
        self.entry_subject = tk.Entry(frame, width=70)
        self.text_body = scrolledtext.ScrolledText(frame, height=5)

        self.entry_to.pack(pady=2)
        self.entry_subject.pack(pady=2)
        self.text_body.pack(pady=5)

        tk.Button(frame, text="Send", command=self.send_mail).pack(pady=5)
        tk.Button(frame, text="Delete Selected Mail", command=self.delete_selected_mail).pack(pady=5)

        # Mail read area
        self.label_read = tk.Label(frame, text="Selected Mail Content", font=("Arial", 12))
        self.text_read = scrolledtext.ScrolledText(frame, height=5)
        self.label_read.pack(pady=5)
        self.text_read.pack(padx=10, pady=5)

        return frame

    def load_mail_list(self):
        try:
            self.sock.sendall(b"LIST")
            data = self.sock.recv(4096).decode()
            self.mailbox = json.loads(data)
            self.mail_listbox.delete(0, tk.END)
            for i, m in enumerate(self.mailbox):
                self.mail_listbox.insert(i, f"[{m['id']}] {m['date']} - {m['subject']} from {m['sender']}")
        except Exception as e:
            messagebox.showerror("Inbox Error", str(e))

    def read_selected_mail(self, event):
        if not self.mail_listbox.curselection():
            return
        idx = self.mail_listbox.curselection()[0]
        mid = self.mailbox[idx]["id"]
        try:
            self.sock.sendall(f"READ::{mid}".encode())
            res = self.sock.recv(4096).decode()
            if res.startswith("READ_OK::"):
                mail_json = res.split("::", 1)[1]
                mail = eval(mail_json)  # 안전하게 하려면 json.loads() 쓰되, 서버 쪽 JSON으로 바꾸기
                self.text_read.delete(1.0, tk.END)
                self.text_read.insert(tk.END, f"From: {mail['sender']}\nTo: {mail['receiver']}\nSubject: {mail['subject']}\n\n{mail['body']}")
            else:
                self.text_read.delete(1.0, tk.END)
                self.text_read.insert(tk.END, "Mail not found.")
        except Exception as e:
            messagebox.showerror("Read Error", str(e))

    def send_mail(self):
        to = self.entry_to.get()
        subj = self.entry_subject.get()
        body = self.text_body.get("1.0", tk.END).strip()
        try:
            self.sock.sendall(f"SEND::{to}::{subj}::{body}".encode())
            res = self.sock.recv(1024).decode()
            if res in ("SEND_OK", "SEND_QUEUED"):
                messagebox.showinfo("Send", "Mail sent successfully.")
                self.entry_to.delete(0, tk.END)
                self.entry_subject.delete(0, tk.END)
                self.text_body.delete("1.0", tk.END)
                self.load_mail_list()
            else:
                messagebox.showerror("Send Failed", res)
        except Exception as e:
            messagebox.showerror("Send Error", str(e))

    def delete_selected_mail(self):
        if not self.mail_listbox.curselection():
            return
        idx = self.mail_listbox.curselection()[0]
        mid = self.mailbox[idx]["id"]
        try:
            self.sock.sendall(f"DELETE::{mid}".encode())
            res = self.sock.recv(1024).decode()
            if res == "DELETE_OK":
                messagebox.showinfo("Delete", "Mail deleted.")
                self.load_mail_list()
                self.text_read.delete(1.0, tk.END)
            else:
                messagebox.showerror("Delete Failed", res)
        except Exception as e:
            messagebox.showerror("Delete Error", str(e))

    def logout(self):
        try:
            self.sock.sendall(b"LOGOUT")
            self.sock.close()
        except:
            pass
        self.username = None
        self.sock = None
        self.show_frame("ServerSelect")


if __name__ == "__main__":
    app = MailClientApp()
    app.refresh_server_list()
    app.mainloop()
