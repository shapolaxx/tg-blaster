import customtkinter as ctk
from storage import make_storage
from telegram_client import TGClient, load_config
from screens.config_screen import ConfigScreen
from screens.auth_screen import AuthScreen
from tabs.templates_tab import TemplatesTab
from tabs.chats_tab import ChatsTab
from tabs.broadcast_tab import BroadcastTab


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TG Blaster")
        self.geometry("720x620")
        self._storage = make_storage()
        self._tg = None
        self.withdraw()
        self.after(100, self._startup)

    def _startup(self):
        config = load_config()
        if not config:
            ConfigScreen(self, on_done=self._startup)
            return
        api_id, api_hash = config
        self._tg = TGClient(api_id, api_hash)
        self._tg.start_loop()
        self._tg.connect()
        if not self._tg.is_authorized():
            AuthScreen(self, self._tg, on_done=self._open_main)
        else:
            self._open_main()

    def _open_main(self):
        self.deiconify()
        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)

        tab1 = tabs.add("Шаблоны")
        tab2 = tabs.add("Чаты")
        tab3 = tabs.add("Рассылка")

        TemplatesTab(tab1, self._storage).pack(fill="both", expand=True)
        ChatsTab(tab2, self._storage).pack(fill="both", expand=True)
        BroadcastTab(tab3, self._storage, self._tg).pack(fill="both", expand=True)

    def _on_closing(self):
        if self._tg:
            self._tg.disconnect()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app._on_closing)
    app.mainloop()
