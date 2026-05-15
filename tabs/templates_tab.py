import uuid
import customtkinter as ctk
from tkinter import filedialog, messagebox
from utils.paste_fix import setup_paste, fix_entry, fix_textbox


class TemplateDialog(ctk.CTkToplevel):
    def __init__(self, parent, storage, template=None, tg_client=None, on_save=None):
        super().__init__(parent)
        self.title("Шаблон")
        self.geometry("500x480")
        self.resizable(False, False)
        self.grab_set()
        self._storage = storage
        self._tg = tg_client
        self._template = template
        self._on_save = on_save
        self._photo_path = template["photo"] if template else ""

        setup_paste(self)

        ctk.CTkLabel(self, text="Название:").pack(anchor="w", padx=20, pady=(15, 0))
        self._name = ctk.CTkEntry(self, width=460)
        self._name.pack(padx=20)
        fix_entry(self._name)
        if template:
            self._name.insert(0, template["name"])

        # Text label row with optional emoji button
        text_label_row = ctk.CTkFrame(self, fg_color="transparent")
        text_label_row.pack(fill="x", padx=20, pady=(10, 0))
        ctk.CTkLabel(text_label_row, text="Текст сообщения:").pack(side="left")
        if tg_client:
            ctk.CTkButton(
                text_label_row,
                text="🎭 Emoji",
                width=90,
                height=24,
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                border_width=1,
                text_color=("gray30", "gray70"),
                command=self._open_emoji_picker,
            ).pack(side="right")
            ctk.CTkLabel(
                text_label_row,
                text="формат: [😀:12345678901]",
                text_color="gray",
                font=ctk.CTkFont(size=10),
            ).pack(side="right", padx=6)

        self._text = ctk.CTkTextbox(self, width=460, height=160)
        self._text.pack(padx=20)
        fix_textbox(self._text)
        if template:
            self._text.insert("1.0", template["text"])

        self._photo_label = ctk.CTkLabel(self, text=self._photo_display(), wraplength=440)
        self._photo_label.pack(pady=(8, 2))

        ctk.CTkButton(self, text="Выбрать медиа", command=self._pick_photo).pack()
        ctk.CTkButton(self, text="Сохранить", command=self._save).pack(pady=12)

    def _photo_display(self):
        return f"Фото: {self._photo_path}" if self._photo_path else "Фото не выбрано"

    def _pick_photo(self):
        path = filedialog.askopenfilename(
            filetypes=[("Media", "*.jpg *.jpeg *.png *.mp4 *.mov *.gif *.webp")]
        )
        if path:
            self._photo_path = path
            self._photo_label.configure(text=self._photo_display())

    def _open_emoji_picker(self):
        from screens.emoji_picker import EmojiPickerDialog
        EmojiPickerDialog(self, self._tg, self._text)

    def _save(self):
        name = self._name.get().strip()
        text = self._text.get("1.0", "end").strip()
        if not name or not text:
            messagebox.showwarning("Ошибка", "Заполните название и текст")
            return
        tid = self._template["id"] if self._template else str(uuid.uuid4())
        photo = self._storage.copy_photo(self._photo_path, tid) if self._photo_path else ""
        templates = self._storage.load_templates()
        entry = {"id": tid, "name": name, "text": text, "photo": photo}
        if self._template:
            templates = [entry if t["id"] == tid else t for t in templates]
        else:
            templates.append(entry)
        self._storage.save_templates(templates)
        self.destroy()
        if self._on_save:
            self._on_save()


class TemplatesTab(ctk.CTkFrame):
    def __init__(self, parent, storage, tg_client=None):
        super().__init__(parent, fg_color="transparent")
        self._storage = storage
        self._tg = tg_client
        self._selected = None
        self._buttons = {}

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(
            header, text="Шаблоны",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=("#111827", "white"),
        ).pack(side="left")

        # Action bar
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(16, 8))
        ctk.CTkButton(
            bar, text="+ Добавить", width=120, height=36,
            fg_color="#F97316", hover_color="#EA6C0A",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._add,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            bar, text="Изменить", width=110, height=36,
            fg_color=("gray85", "#1E293B"), hover_color=("gray78", "#334155"),
            text_color=("#374151", "#E2E8F0"),
            command=self._edit,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            bar, text="Удалить", width=100, height=36,
            fg_color="#EF4444", hover_color="#DC2626",
            command=self._delete,
        ).pack(side="left")

        self._listbox = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._listbox.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self._refresh()

    def _refresh(self):
        for w in self._listbox.winfo_children():
            w.destroy()
        self._selected = None
        self._buttons = {}
        templates = self._storage.load_templates()

        if not templates:
            ctk.CTkLabel(
                self._listbox,
                text="Нет шаблонов\n\nНажмите «+ Добавить» чтобы создать первый шаблон",
                font=ctk.CTkFont(size=13),
                text_color=("gray50", "#475569"),
                justify="center",
            ).pack(expand=True, pady=60)
            return

        for t in templates:
            card = ctk.CTkFrame(
                self._listbox,
                fg_color=("white", "#0F172A"),
                border_width=1,
                border_color=("#E2E8F0", "#1E293B"),
                corner_radius=10,
            )
            card.pack(fill="x", pady=4)

            btn = ctk.CTkButton(
                card, text=t["name"], anchor="w",
                fg_color="transparent",
                hover_color=("gray92", "#1E293B"),
                text_color=("#111827", "white"),
                font=ctk.CTkFont(size=13, weight="bold"),
                corner_radius=8,
                command=lambda tid=t["id"]: self._select(tid),
            )
            btn.pack(side="left", fill="x", expand=True, padx=4, pady=4)
            self._buttons[t["id"]] = btn

            if t.get("photo"):
                ctk.CTkLabel(
                    card, text="МЕДИА",
                    font=ctk.CTkFont(size=9, weight="bold"),
                    text_color="#3B82F6",
                    fg_color=("#DBEAFE", "#1E3A5F"),
                    corner_radius=4, width=44, height=20,
                ).pack(side="right", padx=10)

    def _select(self, tid):
        if self._selected and self._selected in self._buttons:
            self._buttons[self._selected].configure(
                fg_color="transparent", text_color=("#111827", "white")
            )
        self._selected = tid
        self._buttons[tid].configure(
            fg_color=("#DBEAFE", "#1E3A5F"), text_color=("#1D4ED8", "#60A5FA")
        )

    def _add(self):
        TemplateDialog(self, self._storage, tg_client=self._tg, on_save=self._refresh)

    def _edit(self):
        if not self._selected:
            messagebox.showinfo("", "Выберите шаблон")
            return
        template = next((t for t in self._storage.load_templates() if t["id"] == self._selected), None)
        if template:
            TemplateDialog(self, self._storage, template=template, tg_client=self._tg, on_save=self._refresh)

    def _delete(self):
        if not self._selected:
            messagebox.showinfo("", "Выберите шаблон")
            return
        if messagebox.askyesno("Удалить", "Удалить шаблон?"):
            templates = [t for t in self._storage.load_templates() if t["id"] != self._selected]
            self._storage.save_templates(templates)
            self._refresh()
