import threading
import customtkinter as ctk


class EmojiPickerDialog(ctk.CTkToplevel):
    """Fetch user's Telegram custom emoji packs and let the user pick one.

    On click, inserts [EMOJI_CHAR:DOCUMENT_ID] at the cursor position of
    the supplied CTkTextbox widget.
    """

    def __init__(self, parent, tg_client, text_widget):
        super().__init__(parent)
        self.title("Premium Emoji")
        self.geometry("540x420")
        self.resizable(True, True)
        self.grab_set()
        self._tg = tg_client
        self._text_widget = text_widget

        self._status = ctk.CTkLabel(self, text="Загружаю эмодзи паки…", font=ctk.CTkFont(size=13))
        self._status.pack(pady=(20, 8))

        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._hint = ctk.CTkLabel(
            self,
            text="Кликни на эмодзи — он вставится в шаблон",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        )
        self._hint.pack(pady=(0, 8))

        threading.Thread(target=self._load, daemon=True).start()

    # ── Loading ────────────────────────────────────────────────────────────

    def _load(self):
        try:
            packs = self._tg.get_custom_emoji_packs()
        except Exception as exc:
            self.after(0, self._show_error, str(exc))
            return
        self.after(0, self._render, packs)

    def _show_error(self, msg):
        self._status.configure(text=f"Ошибка: {msg}", text_color="red")

    def _render(self, packs):
        if not packs:
            self._status.configure(
                text="Emoji-паков не найдено.\nДобавь emoji-паки в Telegram → Стикеры.",
                text_color="gray",
            )
            return

        self._status.configure(text=f"Найдено паков: {len(packs)}", text_color="gray")

        for pack_title, items in packs:
            ctk.CTkLabel(
                self._scroll,
                text=pack_title,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ).pack(fill="x", pady=(8, 2))

            row_frame = None
            for idx, (char, doc_id) in enumerate(items):
                if idx % 10 == 0:
                    row_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
                    row_frame.pack(fill="x")

                btn = ctk.CTkButton(
                    row_frame,
                    text=char,
                    width=44,
                    height=44,
                    font=ctk.CTkFont(size=20),
                    fg_color="transparent",
                    hover_color=("gray80", "gray30"),
                    corner_radius=8,
                    command=lambda c=char, d=doc_id: self._insert(c, d),
                )
                btn.pack(side="left", padx=2, pady=2)

    # ── Insert ─────────────────────────────────────────────────────────────

    def _insert(self, char, doc_id):
        snippet = f"[{char}:{doc_id}]"
        try:
            tb = self._text_widget._textbox
            tb.insert("insert", snippet)
        except Exception:
            try:
                self._text_widget.insert("insert", snippet)
            except Exception:
                pass
        self.destroy()
