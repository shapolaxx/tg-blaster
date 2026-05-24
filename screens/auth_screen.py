import threading
import customtkinter as ctk
from telethon.errors import SessionPasswordNeededError


class AuthScreen(ctk.CTkToplevel):
    def __init__(self, parent, tg_client, on_done):
        super().__init__(parent)
        self.title("Вход в Telegram")
        self.geometry("420x380")
        self.resizable(False, False)
        self.grab_set()
        self._tg = tg_client
        self._on_done = on_done

        ctk.CTkLabel(self, text="Войдите в Telegram аккаунт", font=ctk.CTkFont(size=14)).pack(pady=(20, 10))

        ctk.CTkLabel(self, text="Номер телефона (напр. +79001234567):").pack(anchor="w", padx=30)
        self._phone = ctk.CTkEntry(self, width=360)
        self._phone.pack(padx=30)

        self._send_btn = ctk.CTkButton(self, text="Получить код", command=self._send_code)
        self._send_btn.pack(pady=10)

        ctk.CTkLabel(self, text="Код из Telegram:").pack(anchor="w", padx=30)
        self._code = ctk.CTkEntry(self, width=360)
        self._code.pack(padx=30)
        self._code.configure(state="disabled")

        self._login_btn = ctk.CTkButton(self, text="Войти", command=self._sign_in, state="disabled")
        self._login_btn.pack(pady=10)

        # 2FA password (hidden until needed)
        self._pwd_label = ctk.CTkLabel(self, text="Облачный пароль (двухфакторная аутентификация):")
        self._pwd = ctk.CTkEntry(self, width=360, show="•")
        self._pwd_btn = ctk.CTkButton(self, text="Подтвердить пароль", command=self._sign_in_password)

        self._status = ctk.CTkLabel(self, text="")
        self._status.pack()

        from utils.paste_fix import setup_paste, fix_entry
        setup_paste(self)
        fix_entry(self._phone)
        fix_entry(self._code)

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self._send_btn.configure(state=state)
        self._login_btn.configure(state=state)

    def _send_code(self):
        phone = self._phone.get().strip()
        if not phone:
            self._status.configure(text="Введите номер телефона", text_color="red")
            return
        self._set_busy(True)
        self._status.configure(text="Отправляем код...", text_color="gray")
        threading.Thread(target=self._do_send_code, args=(phone,), daemon=True).start()

    def _do_send_code(self, phone):
        try:
            self._tg.send_code(phone)
            self.after(0, self._on_code_sent)
        except Exception as e:
            self.after(0, lambda: self._status.configure(text=f"Ошибка: {e}", text_color="red"))
            self.after(0, lambda: self._set_busy(False))

    def _on_code_sent(self):
        self._code.configure(state="normal")
        self._login_btn.configure(state="normal")
        self._send_btn.configure(state="normal")
        self._status.configure(text="Код отправлен", text_color="green")

    def _sign_in(self):
        code = self._code.get().strip()
        if not code:
            self._status.configure(text="Введите код", text_color="red")
            return
        self._set_busy(True)
        self._status.configure(text="Входим...", text_color="gray")
        threading.Thread(target=self._do_sign_in, args=(code,), daemon=True).start()

    def _do_sign_in(self, code):
        try:
            self._tg.sign_in(code)
            self.after(0, self._finish)
        except SessionPasswordNeededError:
            self.after(0, self._show_password_field)
        except Exception as e:
            self.after(0, lambda: self._status.configure(text=f"Ошибка: {e}", text_color="red"))
            self.after(0, lambda: self._set_busy(False))

    def _finish(self):
        self.destroy()
        self._on_done()

    def _show_password_field(self):
        self._login_btn.configure(state="disabled")
        self._status.configure(text="Требуется облачный пароль", text_color="#FF9800")
        self._pwd_label.pack(anchor="w", padx=30, pady=(6, 0))
        self._pwd.pack(padx=30)
        self._pwd_btn.pack(pady=8)
        self._pwd.focus()

    def _sign_in_password(self):
        password = self._pwd.get()
        if not password:
            self._status.configure(text="Введите пароль", text_color="red")
            return
        self._pwd_btn.configure(state="disabled")
        self._status.configure(text="Проверяем пароль...", text_color="gray")
        threading.Thread(target=self._do_sign_in_password, args=(password,), daemon=True).start()

    def _do_sign_in_password(self, password):
        try:
            self._tg.sign_in_password(password)
            self.after(0, self._finish)
        except Exception as e:
            self.after(0, lambda: self._status.configure(text=f"Неверный пароль: {e}", text_color="red"))
            self.after(0, lambda: self._pwd_btn.configure(state="normal"))
            self.after(0, lambda: self._pwd.delete(0, "end"))
