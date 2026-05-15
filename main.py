import customtkinter as ctk
import threading
from storage import make_storage
from telegram_client import TGClient, load_config
from screens.config_screen import ConfigScreen
from screens.auth_screen import AuthScreen
from tabs.dashboard_tab import DashboardTab
from tabs.templates_tab import TemplatesTab
from tabs.chats_tab import ChatsTab
from tabs.broadcast_tab import BroadcastTab
from tabs.history_tab import HistoryTab


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

NAV_ITEMS = [
    ("Дашборд", "dashboard"),
    ("Шаблоны", "templates"),
    ("Чаты", "chats"),
    ("Рассылка", "broadcast"),
    ("История", "history"),
]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TG Blaster")
        self.geometry("920x680")
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._storage = make_storage()
        self._tg = None
        self._tray = None
        self._tabs = {}
        self._nav_buttons = {}
        self._current = None
        self.bind_all("<Control-v>", lambda e: e.widget.event_generate("<<Paste>>"))
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

        sidebar = ctk.CTkFrame(self, width=190, corner_radius=0, fg_color=("gray88", "gray13"))
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(
            sidebar, text="TG Blaster",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(24, 20))

        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._content.pack(side="left", fill="both", expand=True)

        self._tabs["dashboard"] = DashboardTab(self._content, self._storage)
        self._tabs["templates"] = TemplatesTab(self._content, self._storage)
        self._tabs["chats"] = ChatsTab(self._content, self._storage, self._tg)
        self._tabs["broadcast"] = BroadcastTab(self._content, self._storage, self._tg)
        self._tabs["history"] = HistoryTab(self._content, self._storage)

        for label, key in NAV_ITEMS:
            btn = ctk.CTkButton(
                sidebar, text=label, width=170, height=40,
                anchor="w",
                fg_color="transparent",
                text_color=("gray20", "gray80"),
                hover_color=("gray78", "gray25"),
                corner_radius=8,
                command=lambda k=key: self._show(k),
            )
            btn.pack(pady=3, padx=10)
            self._nav_buttons[key] = btn

        self._show("dashboard")
        self._setup_tray()

    def _show(self, key):
        if self._current:
            self._tabs[self._current].pack_forget()
            self._nav_buttons[self._current].configure(
                fg_color="transparent",
                text_color=("gray20", "gray80"),
            )
        self._current = key
        self._tabs[key].pack(fill="both", expand=True, padx=8, pady=8)
        self._nav_buttons[key].configure(
            fg_color=("#3B82F6", "#2563EB"),
            text_color="white",
        )
        if key == "dashboard":
            self._tabs[key].refresh()

    def _setup_tray(self):
        try:
            from PIL import Image
            import pystray
            img = Image.new("RGB", (64, 64), color=(249, 115, 22))
            menu = pystray.Menu(
                pystray.MenuItem("Открыть", self._show_window, default=True),
                pystray.MenuItem("Выход", self._quit_app),
            )
            self._tray = pystray.Icon("TG Blaster", img, "TG Blaster", menu)
            threading.Thread(target=self._tray.run, daemon=True).start()
        except Exception:
            pass

    def _show_window(self, icon=None, item=None):
        self.after(0, self.deiconify)
        self.after(0, self.lift)

    def _quit_app(self, icon=None, item=None):
        self.after(0, self._force_quit)

    def _on_closing(self):
        if self._tray:
            self.withdraw()
        else:
            self._force_quit()

    def _force_quit(self):
        try:
            if self._tray:
                self._tray.stop()
        except Exception:
            pass
        try:
            if self._tg:
                self._tg.disconnect()
        except Exception:
            pass
        self.destroy()
        import os
        os._exit(0)


if __name__ == "__main__":
    app = App()
    app.mainloop()
