import customtkinter as ctk
import threading
from storage import make_storage
from telegram_client import TGClient, load_config, SESSION_FILE, CONFIG_FILE
from screens.config_screen import ConfigScreen
from screens.auth_screen import AuthScreen
from tabs.dashboard_tab import DashboardTab
from tabs.templates_tab import TemplatesTab
from tabs.chats_tab import ChatsTab
from tabs.broadcast_tab import BroadcastTab
from tabs.history_tab import HistoryTab
from utils.paste_fix import setup_paste


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

NAV_ITEMS = [
    ("Дашборд",  "dashboard",  "○"),
    ("Шаблоны",  "templates",  "≡"),
    ("Чаты",     "chats",      "◻"),
    ("Рассылка", "broadcast",  "▷"),
    ("История",  "history",    "◷"),
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
        setup_paste(self)
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

        sidebar = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color=("gray90", "#0F172A"))
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Orange top accent bar
        ctk.CTkFrame(sidebar, height=3, corner_radius=0, fg_color="#F97316").pack(fill="x")

        # Logo
        ctk.CTkLabel(
            sidebar, text="TG Blaster",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#111827", "white"),
        ).pack(pady=(18, 0))
        ctk.CTkLabel(
            sidebar, text="Telegram автопостинг",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "#64748B"),
        ).pack(pady=(2, 16))
        ctk.CTkFrame(sidebar, height=1, corner_radius=0, fg_color=("gray78", "#1E293B")).pack(fill="x")

        self._content = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray95", "#020617"))
        self._content.pack(side="left", fill="both", expand=True)

        self._tabs["dashboard"] = DashboardTab(self._content, self._storage)
        self._tabs["templates"] = TemplatesTab(self._content, self._storage, self._tg)
        self._tabs["chats"] = ChatsTab(self._content, self._storage, self._tg)
        self._tabs["broadcast"] = BroadcastTab(self._content, self._storage, self._tg)
        self._tabs["history"] = HistoryTab(self._content, self._storage, self._tg)

        self._nav_stripes = {}
        for label, key, icon in NAV_ITEMS:
            row = ctk.CTkFrame(sidebar, fg_color="transparent", height=44)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            stripe = ctk.CTkFrame(row, width=3, corner_radius=0, fg_color="transparent")
            stripe.pack(side="left", fill="y")
            stripe.pack_propagate(False)
            self._nav_stripes[key] = stripe

            btn = ctk.CTkButton(
                row, text=f"  {icon}  {label}", height=44,
                anchor="w",
                fg_color="transparent",
                text_color=("gray30", "#94A3B8"),
                hover_color=("gray82", "#1E293B"),
                corner_radius=0,
                font=ctk.CTkFont(size=13),
                command=lambda k=key: self._show(k),
            )
            btn.pack(side="left", fill="both", expand=True)
            self._nav_buttons[key] = btn

        self._show("dashboard")

        # Bottom section
        ctk.CTkFrame(sidebar, height=1, corner_radius=0, fg_color=("gray78", "#1E293B")).pack(side="bottom", fill="x")
        ctk.CTkButton(
            sidebar, text="  ← Выйти из аккаунта", height=36,
            anchor="w", fg_color="transparent",
            text_color=("gray50", "#475569"), hover_color=("gray82", "#1E293B"),
            corner_radius=0, font=ctk.CTkFont(size=12),
            command=self._logout,
        ).pack(side="bottom", fill="x")
        ctk.CTkButton(
            sidebar, text="  ⚙ Сменить API", height=36,
            anchor="w", fg_color="transparent",
            text_color=("gray50", "#475569"), hover_color=("gray82", "#1E293B"),
            corner_radius=0, font=ctk.CTkFont(size=12),
            command=self._change_api,
        ).pack(side="bottom", fill="x")

        self._setup_tray()

    def _show(self, key):
        if self._current:
            self._tabs[self._current].pack_forget()
            self._nav_buttons[self._current].configure(fg_color="transparent", text_color=("gray30", "#94A3B8"))
            self._nav_stripes[self._current].configure(fg_color="transparent")
        self._current = key
        self._tabs[key].pack(fill="both", expand=True, padx=0, pady=0)
        self._nav_buttons[key].configure(fg_color=("gray83", "#1E293B"), text_color=("#1E40AF", "#60A5FA"))
        self._nav_stripes[key].configure(fg_color="#F97316")
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

    def _change_api(self):
        from tkinter import messagebox
        if not messagebox.askyesno("Сменить API", "Сбросить API credentials?\nПри следующем запуске потребуется ввести новые API ID и Hash."):
            return
        try:
            CONFIG_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        import os
        os._exit(0)

    def _logout(self):
        from tkinter import messagebox
        if not messagebox.askyesno("Выйти из аккаунта", "Выйти из текущего аккаунта?\nПри следующем запуске потребуется войти снова."):
            return
        try:
            if self._tg:
                self._tg.logout()
        except Exception:
            pass
        for suffix in (".session", ".session-journal"):
            try:
                Path(SESSION_FILE + suffix).unlink(missing_ok=True)
            except Exception:
                pass
        import os
        os._exit(0)

    def _on_closing(self):
        self._force_quit()

    def _force_quit(self, icon=None, item=None):
        try:
            if self._tray:
                self._tray.stop()
        except Exception:
            pass
        import os
        os._exit(0)


if __name__ == "__main__":
    app = App()
    app.mainloop()
