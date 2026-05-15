import threading
import customtkinter as ctk
from utils.paste_fix import fix_entry, setup_paste


class EmojiPickerDialog(ctk.CTkToplevel):
    """Pick premium emoji from a Telegram emoji pack and insert into template text."""

    def __init__(self, parent, tg_client, text_widget):
        super().__init__(parent)
        self.title("Premium Emoji")
        self.geometry("560x500")
        self.resizable(True, True)
        self.grab_set()
        setup_paste(self)
        self._tg = tg_client
        self._text_widget = text_widget

        # ── URL loader ────────────────────────────────────────────────────
        url_frame = ctk.CTkFrame(self)
        url_frame.pack(fill="x", padx=12, pady=(12, 4))

        ctk.CTkLabel(url_frame, text="Ссылка на пак:", anchor="w").pack(side="left", padx=(4, 6))
        self._url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="t.me/addemoji/PackName  или  короткое имя",
            width=320,
        )
        self._url_entry.pack(side="left", fill="x", expand=True)
        fix_entry(self._url_entry)

        ctk.CTkButton(
            url_frame, text="📋", width=36, command=self._paste_url,
            fg_color="transparent", hover_color=("gray75", "gray30"),
        ).pack(side="left", padx=(4, 0))

        self._load_btn = ctk.CTkButton(
            url_frame, text="Загрузить", width=90, command=self._load_by_url
        )
        self._load_btn.pack(side="left", padx=(4, 4))

        ctk.CTkLabel(
            self,
            text="Найди emoji-пак в Telegram → скопируй ссылку → вставь сюда",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=16)

        # ── Status + scroll ───────────────────────────────────────────────
        self._status = ctk.CTkLabel(self, text="", text_color="gray")
        self._status.pack(pady=(6, 2))

        self._scroll = ctk.CTkScrollableFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        ctk.CTkLabel(
            self,
            text="Кликни на emoji — он вставится в шаблон как [😀:ID]",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        ).pack(pady=(0, 8))

        # Auto-load user's own packs
        self._status.configure(text="Загружаю твои паки…")
        threading.Thread(target=self._load_my_packs, daemon=True).start()

    def _paste_url(self):
        try:
            text = self.clipboard_get()
            inner = getattr(self._url_entry, "_entry", None)
            if inner:
                inner.delete(0, "end")
                inner.insert(0, text.strip())
            else:
                self._url_entry.delete(0, "end")
                self._url_entry.insert(0, text.strip())
        except Exception:
            pass

    # ── Loading ────────────────────────────────────────────────────────────

    def _load_my_packs(self):
        try:
            packs = self._tg.get_custom_emoji_packs()
        except Exception as exc:
            self.after(0, self._status.configure, {"text": f"Ошибка: {exc}", "text_color": "red"})
            return
        if packs:
            self.after(0, self._render_packs, packs)
        else:
            self.after(
                0,
                self._status.configure,
                {"text": "Паков нет — вставь ссылку выше или добавь паки в Telegram", "text_color": "gray"},
            )

    def _load_by_url(self):
        url = self._url_entry.get().strip()
        if not url:
            return
        self._load_btn.configure(state="disabled", text="…")
        self._status.configure(text="Загружаю…", text_color="gray")
        threading.Thread(target=self._fetch_by_url, args=(url,), daemon=True).start()

    def _fetch_by_url(self, url):
        try:
            title, items = self._tg.load_emoji_pack_by_name(url)
        except Exception as exc:
            self.after(0, self._on_url_error, str(exc))
            return
        self.after(0, self._on_url_done, title, items)

    def _on_url_error(self, msg):
        self._status.configure(text=f"Не нашёл пак: {msg}", text_color="red")
        self._load_btn.configure(state="normal", text="Загрузить")

    def _on_url_done(self, title, items):
        self._load_btn.configure(state="normal", text="Загрузить")
        self._status.configure(text=f"Загружен: {title}  ({len(items)} emoji)", text_color="#4CAF50")
        self._render_packs([(title, items)], clear=True)

    # ── Rendering ──────────────────────────────────────────────────────────

    def _render_packs(self, packs, clear=False):
        if clear:
            for w in self._scroll.winfo_children():
                w.destroy()

        emoji_font = ctk.CTkFont(family="Segoe UI Emoji", size=22)
        small_font = ctk.CTkFont(size=9)

        for pack_title, items in packs:
            ctk.CTkLabel(
                self._scroll,
                text=pack_title,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ).pack(fill="x", pady=(8, 2))

            # Count duplicates so user can distinguish same-char stickers
            char_count: dict[str, int] = {}
            char_idx: dict[str, int] = {}
            for char, _ in items:
                char_count[char] = char_count.get(char, 0) + 1

            row_frame = None
            for idx, (char, doc_id) in enumerate(items):
                if idx % 8 == 0:
                    row_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
                    row_frame.pack(fill="x")

                # Number stickers that share the same unicode char
                char_idx[char] = char_idx.get(char, 0) + 1
                label = char if char_count[char] == 1 else f"{char}{char_idx[char]}"

                cell = ctk.CTkFrame(row_frame, fg_color="transparent", width=52, height=52)
                cell.pack(side="left", padx=2, pady=2)
                cell.pack_propagate(False)

                ctk.CTkButton(
                    cell,
                    text=label,
                    width=50,
                    height=50,
                    font=emoji_font,
                    fg_color="transparent",
                    hover_color=("gray80", "gray30"),
                    corner_radius=8,
                    command=lambda c=char, d=doc_id: self._insert(c, d),
                ).place(relx=0, rely=0, relwidth=1, relheight=1)

    # ── Insert ─────────────────────────────────────────────────────────────

    def _insert(self, char, doc_id):
        snippet = f"[{char}:{doc_id}]"
        try:
            self._text_widget._textbox.insert("insert", snippet)
        except Exception:
            try:
                self._text_widget.insert("insert", snippet)
            except Exception:
                pass
        self.destroy()
