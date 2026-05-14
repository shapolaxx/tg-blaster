import customtkinter as ctk


class AuthScreen(ctk.CTkToplevel):
    def __init__(self, parent, tg_client, on_done):
        super().__init__(parent)
        self.title("Вход в Telegram")
        self.geometry("420x320")
        self.resizable(False, False)
        self.grab_set()
        self._tg = tg_client
        self._on_done = on_done

        ctk.CTkLabel(self, text="Войдите в Telegram аккаунт", font=ctk.CTkFont(size=14)).pack(pady=(20, 10))

        ctk.CTkLabel(self, text="Номер телефона (напр. +79001234567):").pack(anchor="w", padx=30)
        self._phone = ctk.CTkEntry(self, width=360)
        self._phone.pack(padx=30)

        ctk.CTkButton(self, text="Получить код", command=self._send_code).pack(pady=10)

        ctk.CTkLabel(self, text="Код из Telegram:").pack(anchor="w", padx=30)
        self._code = ctk.CTkEntry(self, width=360)
        self._code.pack(padx=30)
        self._code.configure(state="disabled")

        self._login_btn = ctk.CTkButton(self, text="Войти", command=self._sign_in, state="disabled")
        self._login_btn.pack(pady=10)

        self._status = ctk.CTkLabel(self, text="")
        self._status.pack()

    def _send_code(self):
        phone = self._phone.get().strip()
        if not phone:
            self._status.configure(text="Введите номер телефона", text_color="red")
            return
        try:
            self._tg.send_code(phone)
            self._code.configure(state="normal")
            self._login_btn.configure(state="normal")
            self._status.configure(text="Код отправлен", text_color="green")
        except Exception as e:
            self._status.configure(text=f"Ошибка: {e}", text_color="red")

    def _sign_in(self):
        code = self._code.get().strip()
        if not code:
            self._status.configure(text="Введите код", text_color="red")
            return
        try:
            self._tg.sign_in(code)
            self.destroy()
            self._on_done()
        except Exception as e:
            self._status.configure(text=f"Ошибка: {e}", text_color="red")
