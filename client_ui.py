import customtkinter as ctk
import socket, json
from tkinter import messagebox

DNS_HOST, DNS_PORT = "127.0.0.1", 4000

class PotatoMailApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Potato Mail")
        self.geometry("1200x800")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.server_info = None
        self.sock = None
        self.username = None
        self.mailbox = []

        self.build_server_select_frame()

    def build_server_select_frame(self):
        self.clear_window()
        frame = ctk.CTkFrame(self, corner_radius=12)
        frame.pack(expand=True, fill="both", padx=60, pady=60)

        ctk.CTkLabel(frame, text="Select Mail Server", font=("Arial", 32, "bold")).pack(pady=(10,30))
        self.server_list_frame = ctk.CTkScrollableFrame(frame, height=350, width=700)
        self.server_list_frame.pack(pady=10)
        ctk.CTkButton(frame, text="Refresh", width=200, command=self.refresh_servers).pack(pady=(20,5))
        ctk.CTkButton(frame, text="Exit", width=200, command=self.destroy).pack()

        self.refresh_servers()

    def refresh_servers(self):
        for w in self.server_list_frame.winfo_children():
            w.destroy()
        try:
            with socket.create_connection((DNS_HOST, DNS_PORT)) as s:
                s.sendall(b'{"type":"LIST"}')
                data = json.loads(s.recv(4096).decode())
            servers = data.get("servers", {})
            if not servers:
                ctk.CTkLabel(self.server_list_frame, text="(No servers found)", text_color="gray").pack(pady=20)
            for name, info in servers.items():
                btn = ctk.CTkButton(
                    self.server_list_frame,
                    text=f"{name}  ({info['ip']}:{info['port']})",
                    width=650,
                    height=60,
                    command=lambda n=name: self.select_server(n),
                )
                btn.pack(pady=8)
        except Exception as e:
            messagebox.showerror("DNS Error", str(e))

    def select_server(self, name):
        try:
            with socket.create_connection((DNS_HOST, DNS_PORT)) as s:
                s.sendall(json.dumps({"type":"QUERY","server":name}).encode())
                info = json.loads(s.recv(1024).decode())
            self.server_info = {"ip":info["ip"], "port":info["port"]}
            self.build_login_frame()
        except Exception as e:
            messagebox.showerror("Error", f"Cannot query server: {e}")

    def build_login_frame(self):
        self.clear_window()
        frame = ctk.CTkFrame(self, corner_radius=12)
        frame.pack(expand=True, fill="both", padx=60, pady=60)

        ctk.CTkLabel(frame, text="Login", font=("Arial", 32, "bold")).pack(pady=(10,30))
        self.login_id = ctk.CTkEntry(frame, placeholder_text="User ID", width=400)
        self.login_pw = ctk.CTkEntry(frame, placeholder_text="Password", show="*", width=400)
        self.login_info = ctk.CTkLabel(frame, text="", text_color="red")

        self.login_id.pack(pady=10)
        self.login_pw.pack(pady=10)
        ctk.CTkButton(frame, text="Login", width=200, command=self.login).pack(pady=(30,10))
        self.login_info.pack()

    def login(self):
        uid, pw = self.login_id.get(), self.login_pw.get()
        try:
            self.sock = socket.create_connection((self.server_info["ip"], self.server_info["port"]))
            self.sock.sendall(f"LOGIN::{uid}::{pw}".encode())
            res = self.sock.recv(1024).decode()
            if res == "OK":
                self.username = uid
                self.build_main_frame()
            else:
                messagebox.showerror("Login Failed", "Invalid credentials. Please select server again.")
                self.build_server_select_frame()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.build_server_select_frame()

    def build_main_frame(self):
        self.clear_window()
        container = ctk.CTkFrame(self)
        container.pack(expand=True, fill="both")

        menu = ctk.CTkFrame(container, width=240, fg_color="#1f1f1f")
        menu.pack(side="left", fill="y", padx=10, pady=10)
        ctk.CTkLabel(menu, text="Potato Mail", font=("Arial", 24, "bold")).pack(pady=(20,40))
        ctk.CTkButton(menu, text="Inbox", width=200, command=self.show_inbox).pack(pady=12)
        ctk.CTkButton(menu, text="Compose", width=200, command=self.show_compose).pack(pady=12)
        ctk.CTkButton(menu, text="Logout", width=200, command=self.logout).pack(pady=(40,10))

        self.body = ctk.CTkFrame(container)
        self.body.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        self.show_inbox()

    def show_inbox(self):
        self.clear_body()
        left = ctk.CTkFrame(self.body)
        left.pack(side="left", fill="y", padx=(0,10))

        ctk.CTkLabel(left, text="Inbox", font=("Arial", 24, "bold")).pack(pady=(0,15))
        self.inbox_frame = ctk.CTkScrollableFrame(left, width=350, height=550)
        self.inbox_frame.pack()

        right = ctk.CTkFrame(self.body)
        right.pack(side="right", expand=True, fill="both")

        self.read_subject = ctk.CTkLabel(right, text="", font=("Arial", 20, "bold"))
        self.read_subject.pack(anchor="w", pady=(0,8))
        self.read_meta = ctk.CTkLabel(right, text="", font=("Arial", 12), text_color="gray")
        self.read_meta.pack(anchor="w", pady=(0,15))
        self.read_body = ctk.CTkTextbox(right, width=650, height=480, corner_radius=8)
        self.read_body.pack(expand=True, fill="both")

        self.refresh_inbox()

    def refresh_inbox(self):
        for w in self.inbox_frame.winfo_children():
            w.destroy()
        try:
            self.sock.sendall(b"LIST")
            self.mailbox = json.loads(self.sock.recv(4096).decode())
            if not self.mailbox:
                ctk.CTkLabel(self.inbox_frame, text="(No mail)", text_color="gray").pack(pady=20)
                return
            for m in self.mailbox:
                btn = ctk.CTkButton(
                    self.inbox_frame,
                    text=f"{m['subject']}\n{m['date']}",
                    width=330, height=70,
                    fg_color="#2a2a2a", hover_color="#333333",
                    command=lambda mid=m["id"]: self.load_mail(mid)
                )
                btn.pack(pady=6)
        except Exception as e:
            messagebox.showerror("Inbox Error", str(e))

    def load_mail(self, mid):
        try:
            self.sock.sendall(f"READ::{mid}".encode())
            res = self.sock.recv(4096).decode()
            if res.startswith("READ_OK::"):
                m = json.loads(res.split("::",1)[1].replace("'", '"'))
                self.read_subject.configure(text=m["subject"])
                self.read_meta.configure(text=f"From: {m['sender']}    Date: {m['date']}")
                self.read_body.delete("1.0", "end")
                self.read_body.insert("end", m["body"])

                right = self.body.winfo_children()[1]
                for w in right.winfo_children():
                    if isinstance(w, ctk.CTkButton) and w.cget("text") == "Delete":
                        w.destroy()
                        
                delete_btn = ctk.CTkButton(right, text="Delete", width=100, command=lambda mail_id=m["id"]: self.delete_mail(mail_id))
                delete_btn.pack(anchor="e", pady=(10, 0))
            else:
                self.read_subject.configure(text="")
                self.read_meta.configure(text="")
                self.read_body.delete("1.0", "end")
                self.read_body.insert("end", "Mail not found.")
        except Exception as e:
            messagebox.showerror("Read Error", str(e))

    def show_compose(self):
        self.clear_body()
        ctk.CTkLabel(self.body, text="Compose Mail", font=("Arial", 24, "bold")).pack(pady=(0,20))
        self.to_entry = ctk.CTkEntry(self.body, placeholder_text="To (user@server)", width=700)
        self.subject_entry = ctk.CTkEntry(self.body, placeholder_text="Subject", width=700)
        self.body_text = ctk.CTkTextbox(self.body, width=700, height=450, corner_radius=8)

        self.to_entry.pack(pady=12)
        self.subject_entry.pack(pady=12)
        self.body_text.pack(pady=12)
        ctk.CTkButton(self.body, text="Send", width=140, command=self.send_mail).pack(pady=(10,0))

    def send_mail(self):
        to = self.to_entry.get().strip()
        subj = self.subject_entry.get().strip()
        body = self.body_text.get("1.0", "end").strip()
        if not to or not subj:
            messagebox.showwarning("Input Error", "To and Subject are required.")
            return
        try:
            self.sock.sendall(f"SEND::{to}::{subj}::{body}".encode())
            res = self.sock.recv(1024).decode()
            if res in ("SEND_OK", "SEND_QUEUED"):
                messagebox.showinfo("Success", "Mail sent successfully.")
                self.show_inbox()
            else:
                messagebox.showerror("Send Failed", res)
        except Exception as e:
            messagebox.showerror("Send Error", str(e))

    def delete_mail(self, mid):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this mail?"):
            try:
                self.sock.sendall(f"DELETE::{mid}".encode())
                res = self.sock.recv(1024).decode()
                if res == "DELETE_OK":
                    messagebox.showinfo("Success", "Mail deleted.")
                    self.show_inbox()
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
        self.build_server_select_frame()

    def clear_window(self):
        for w in self.winfo_children():
            w.destroy()
    def clear_body(self):
        for w in getattr(self, 'body', []).winfo_children():
            w.destroy()


if __name__ == "__main__":
    app = PotatoMailApp()
    app.mainloop()
