import customtkinter as ctk
import pymysql
import socket

# SMTP 서버와 연결 함수
def send_to_smtp_server(mail):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', 1025))
            s.recv(1024)

            s.sendall(b"HELO dku.edu\r\n")
            s.recv(1024)

            s.sendall(f"MAIL FROM:<sender@dku.edu>\r\n".encode())
            s.recv(1024)

            s.sendall(f"RCPT TO:<{mail['to']}>\r\n".encode())
            s.recv(1024)

            s.sendall(b"DATA\r\n")
            s.recv(1024)

            body = f"Subject: {mail['subject']}\r\n\r\n{mail['body']}\r\n.\r\n"
            s.sendall(body.encode())
            s.recv(1024)

            s.sendall(b"QUIT\r\n")
            s.recv(1024)
            return True
    except Exception as e:
        print("SMTP 오류:", e)
        return False

# 사용자 등록 함수
def register_user():
    username = username_entry.get()
    password = password_entry.get()

    if username and password:
        try:
            conn = pymysql.connect(
                host='127.0.0.1', user='root', password='bk051014',
                database='user_mgmt', charset='utf8mb4'
            )
            cursor = conn.cursor()
            sql = "INSERT IGNORE INTO users (username, password) VALUES (%s, %s)"
            cursor.execute(sql, (username, password))
            conn.commit()
            info_label.configure(text="Registered. Please log in.")
        except Exception as e:
            print("MySQL 오류:", e)
            info_label.configure(text=f"Error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

# 로그인 함수
def login_user():
    username = username_entry.get()
    password = password_entry.get()

    if username and password:
        try:
            conn = pymysql.connect(
                host='127.0.0.1', user='root', password='bk051014',
                database='user_mgmt', charset='utf8mb4'
            )
            cursor = conn.cursor()
            sql = "SELECT * FROM users WHERE username=%s AND password=%s"
            cursor.execute(sql, (username, password))
            result = cursor.fetchone()
            if result:
                login_frame.pack_forget()
                main_frame.pack(fill="both", expand=True)
                show_frame(frame_compose)
            else:
                info_label.configure(text="Invalid login. Try again.")
        except Exception as e:
            print("MySQL 오류:", e)
            info_label.configure(text=f"Error: {str(e)}")
        finally:
            cursor.close()
            conn.close()

# GUI 설정
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("DKU Networking Mail")
app.geometry("900x600")

sent_box = []

# 로그인 프레임
login_frame = ctk.CTkFrame(app)
login_frame.pack(expand=True)

ctk.CTkLabel(login_frame, text="Welcome to DKU Mail", font=("Arial", 24, "bold")).pack(padx=40, pady=40)
username_entry = ctk.CTkEntry(login_frame, placeholder_text="Username", width=300)
password_entry = ctk.CTkEntry(login_frame, placeholder_text="Password", show="*", width=300)
login_button = ctk.CTkButton(login_frame, text="Login", command=login_user)
register_button = ctk.CTkButton(login_frame, text="Register", command=register_user)
info_label = ctk.CTkLabel(login_frame, text="", text_color="gray")

username_entry.pack(pady=5)
password_entry.pack(pady=5)
login_button.pack(pady=5)
register_button.pack(pady=5)
info_label.pack(pady=5)

main_frame = ctk.CTkFrame(app)
frame_menu = ctk.CTkFrame(main_frame, width=200, fg_color="#f0f0f0")
frame_menu.pack(side="left", fill="y")
frame_main = ctk.CTkFrame(main_frame, fg_color="white")
frame_main.pack(side="right", fill="both", expand=True)

frame_compose = ctk.CTkFrame(frame_main, fg_color="white")
to_entry = ctk.CTkEntry(frame_compose, placeholder_text="To", width=700, height=35)
subject_entry = ctk.CTkEntry(frame_compose, placeholder_text="Subject", width=700, height=35)
body_text = ctk.CTkTextbox(frame_compose, width=700, height=350, fg_color="#fcfcfc")
send_button = ctk.CTkButton(frame_compose, text="Send", fg_color="#4caf50", hover_color="#45a049", corner_radius=8)

to_entry.pack(pady=(20, 10))
subject_entry.pack(pady=(0, 10))
body_text.pack(pady=(0, 10))
send_button.pack(pady=10)

frame_inbox = ctk.CTkFrame(frame_main, fg_color="white")
ctk.CTkLabel(frame_inbox, text="Inbox (coming soon)", font=("Arial", 16)).pack(pady=200)

frame_sent = ctk.CTkFrame(frame_main, fg_color="white")
sent_listbox = ctk.CTkTextbox(frame_sent, width=750, height=400, fg_color="#fcfcfc")
sent_listbox.pack(pady=20, padx=20)

def show_frame(frame):
    for f in (frame_compose, frame_inbox, frame_sent):
        f.pack_forget()
    frame.pack(fill="both", expand=True, pady=20)

def send_mail():
    mail = {
        "to": to_entry.get(),
        "subject": subject_entry.get(),
        "body": body_text.get("0.0", "end").strip()
    }
    if mail["to"] and mail["subject"] and mail["body"]:
        if send_to_smtp_server(mail):
            sent_box.append(mail)
            to_entry.delete(0, "end")
            subject_entry.delete(0, "end")
            body_text.delete("0.0", "end")
            update_sent_view()
            show_frame(frame_sent)
        else:
            info_label.configure(text="메일 전송 실패")

def update_sent_view():
    sent_listbox.delete("0.0", "end")
    for i, mail in enumerate(sent_box, 1):
        sent_listbox.insert("end", f"{i}. {mail['subject']} → {mail['to']}\n")

send_button.configure(command=send_mail)

title_label = ctk.CTkLabel(frame_menu, text="DKU Mail", font=("Arial", 22, "bold"))
title_label.pack(pady=40, padx=40)

compose_btn = ctk.CTkButton(frame_menu, text="Compose", width=160, command=lambda: show_frame(frame_compose))
inbox_btn = ctk.CTkButton(frame_menu, text="Inbox", width=160, command=lambda: show_frame(frame_inbox), fg_color="#e0e0e0")
sent_btn = ctk.CTkButton(frame_menu, text="Sent", width=160, command=lambda: show_frame(frame_sent), fg_color="#cce5e5")

compose_btn.pack(pady=12)
inbox_btn.pack(pady=12)
sent_btn.pack(pady=12)

app.mainloop()
