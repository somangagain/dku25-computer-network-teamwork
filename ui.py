import customtkinter as ctk

# GUI Setup
ctk.set_appearance_mode("dark")
ctk.set_appearance_mode("dark-blue")

# App Instantiation
app = ctk.CTk()
app.title("Potato Mail")
app.geometry("720x480")

# Login frame
login_frame = ctk.CTkFrame(app)
ctk.CTkLabel(login_frame, text="Login to Potato Mail", font=("Arial", 24, "bold")).pack(padx=24, pady=24)

login_entry_id = ctk.CTkEntry(login_frame, placeholder_text="ID", width=320)
login_entry_password = ctk.CTkEntry(login_frame, placeholder_text="Password", show="*", width=320)
login_button_confirm = ctk.CTkButton(login_frame, text="Login", width=320)
login_button_register = ctk.CTkButton(login_frame, text="Register", width=320)
login_label_info = ctk.CTkLabel(login_frame, text="", text_color="gray")

login_entry_id.pack(pady=4, padx=24)
login_entry_password.pack(pady=4, padx=24)
login_button_confirm.pack(pady=4)
login_button_register.pack(pady=4)
login_label_info.pack(pady=4)

# Register frame
register_frame = ctk.CTkFrame(app)
ctk.CTkLabel(register_frame, text="Register to Potato Mail", font=("Arial", 24, "bold")).pack(padx=24, pady=24)

register_entry_id = ctk.CTkEntry(register_frame, placeholder_text="ID", width=320)
register_entry_password = ctk.CTkEntry(register_frame, placeholder_text="Password", show="*", width=320)
register_entry_password_confirm = ctk.CTkEntry(register_frame, placeholder_text="Confirm Password", show="*", width=320)
register_button_confirm = ctk.CTkButton(register_frame, text="Register", width=320)
register_button_login = ctk.CTkButton(register_frame, text="Login", width=320)
register_label_info = ctk.CTkLabel(register_frame, text="", text_color="gray")

register_entry_id.pack(pady=4, padx=24)
register_entry_password.pack(pady=4, padx=24)
register_entry_password_confirm.pack(pady=4, padx=24)
register_button_confirm.pack(pady=4)
register_button_login.pack(pady=4)
register_label_info.pack(pady=4)

# Main frame
main_frame = ctk.CTkFrame(app)

# Main frame - menu
main_frame_menu = ctk.CTkFrame(main_frame, width=200, fg_color="#f0f0f0")
main_frame_menu.pack(side="left", fill="y")

main_frame_menu_title = ctk.CTkLabel(main_frame_menu, text="Potato Mail", font=("Arial", 24, "bold"), text_color="black")
main_frame_menu_button_inbox = ctk.CTkButton(main_frame_menu, text="Inbox", width=160)
main_frame_menu_button_compose = ctk.CTkButton(main_frame_menu, text="Compose", width=160)
main_frame_menu_button_sent = ctk.CTkButton(main_frame_menu, text="Sent", width=160)

main_frame_menu_title.pack(pady=40, padx=40)
main_frame_menu_button_inbox.pack(pady=8)
main_frame_menu_button_compose.pack(pady=8)
main_frame_menu_button_sent.pack(pady=8)

# Main frame - body
main_frame_body = ctk.CTkFrame(main_frame, fg_color="white")
main_frame_body.pack(side="right", fill="both", expand=True)

# Main frame - body - inbox
main_frame_body_inbox = ctk.CTkFrame(main_frame_body, fg_color="white")
main_frame_body_inbox_listbox = ctk.CTkTextbox(main_frame_body_inbox, width=520, fg_color="#fcfcfc")
main_frame_body_inbox_listbox.pack(pady=24, padx=24)

# Main frame - body - compose
main_frame_body_compose = ctk.CTkFrame(main_frame_body, fg_color="white")
main_frame_body_compose_entry_to = ctk.CTkEntry(main_frame_body_compose, placeholder_text="To", width=520, height=35)
main_frame_body_compose_entry_subject = ctk.CTkEntry(main_frame_body_compose, placeholder_text="Subject", width=520, height=35)
main_frame_body_compose_text_body = ctk.CTkTextbox(main_frame_body_compose, width=520, height=350)
main_frame_menu_button_send = ctk.CTkButton(main_frame_body_compose, text="Send", fg_color="#4caf50", hover_color="#45a049", corner_radius=8)

main_frame_body_compose_entry_to.pack(pady=(20, 8))
main_frame_body_compose_entry_subject.pack(pady=(0, 8))
main_frame_body_compose_text_body.pack(pady=(0, 8))
main_frame_menu_button_send.pack(pady=8)

# Main frame - body - sent
main_frame_body_sent = ctk.CTkFrame(main_frame_body, fg_color="white")
main_frame_body_sent_listbox = ctk.CTkTextbox(main_frame_body_sent, width=750, height=400, fg_color="#fcfcfc")
main_frame_body_sent_listbox.pack(pady=24, padx=24)

# frame transition
def frame_show(frame, fill="none"):
    for f in (login_frame, register_frame, main_frame): f.pack_forget()
    frame.pack(expand=True, fill=fill)

def frame_main_show(frame, fill="none"):
    for f in (main_frame_body_inbox, main_frame_body_compose, main_frame_body_sent): f.pack_forget()
    frame.pack(expand=True, fill=fill)

login_button_register.configure(command=lambda: frame_show(register_frame))
register_button_login.configure(command=lambda: frame_show(login_frame))

main_frame_menu_button_inbox.configure(command=lambda: frame_main_show(main_frame_body_inbox))
main_frame_menu_button_compose.configure(command=lambda: frame_main_show(main_frame_body_compose))
main_frame_menu_button_sent.configure(command=lambda: frame_main_show(main_frame_body_sent))

# initialization
frame_show(main_frame, fill="both")
frame_main_show(main_frame_body_compose)

# start app
app.mainloop()