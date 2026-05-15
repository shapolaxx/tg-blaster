import customtkinter as ctk
from telegram_client import save_config


class ConfigScreen(ctk.CTkToplevel):
    def __init__(self, parent, on_done):
        super().__init__(parent)
        self.title("Настройка API")
        self.geometry("420x260")
        self.resizable(False, False)
        self.grab_set()
        self._on_done = on_done

        ctk.CTkLabel(self, text="Введите данные с my.telegram.org", font=ctk.CTkFont(size=14)).pack(pady=(20, 10))

        ctk.CTkLabel(self, text="API ID:").pack(anchor="w", padx=30)
        self._api_id = ctk.CTkEntry(self, width=360)
        self._api_id.pack(padx=30)

        ctk.CTkLabel(self, text="API Hash:").pack(anchor="w", padx=30, pady=(10, 0))
        self._api_hash = ctk.CTkEntry(self, width=360)
        self._api_hash.pack(padx=30)

        self._error = ctk.CTkLabel(self, text="", text_color="red")
        self._error.pack(pady=5)

        ctk.CTkButton(self, text="Сохранить", command=self._save).pack()
        from utils.paste_fix import setup_paste, fix_entry
        setup_paste(self)
        fix_entry(self._api_id)
        fix_entry(self._api_hash)

    def _save(self):
        api_id = self._api_id.get().strip()
        api_hash = self._api_hash.get().strip()
        if not api_id.isdigit() or not api_hash:
            self._error.configure(text="Заполните оба поля корректно")
            return
        save_config(api_id, api_hash)
        self.destroy()
        self._on_done()
