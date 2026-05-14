import uuid
import customtkinter as ctk
from tkinter import filedialog, messagebox


class TemplateDialog(ctk.CTkToplevel):
    def __init__(self, parent, storage, template=None, on_save=None):
        super().__init__(parent)
        self.title("Шаблон")
        self.geometry("500x440")
        self.resizable(False, False)
        self.grab_set()
        self._storage = storage
        self._template = template
        self._on_save = on_save
        self._photo_path = template["photo"] if template else ""

        ctk.CTkLabel(self, text="Название:").pack(anchor="w", padx=20, pady=(15, 0))
        self._name = ctk.CTkEntry(self, width=460)
        self._name.pack(padx=20)
        if template:
            self._name.insert(0, template["name"])

        ctk.CTkLabel(self, text="Текст сообщения:").pack(anchor="w", padx=20, pady=(10, 0))
        self._text = ctk.CTkTextbox(self, width=460, height=160)
        self._text.pack(padx=20)
        if template:
            self._text.insert("1.0", template["text"])

        self._photo_label = ctk.CTkLabel(self, text=self._photo_display(), wraplength=440)
        self._photo_label.pack(pady=(8, 2))

        ctk.CTkButton(self, text="Выбрать фото", command=self._pick_photo).pack()
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
    def __init__(self, parent, storage):
        super().__init__(parent)
        self._storage = storage
        self._selected = None

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(btn_frame, text="Добавить", width=110, command=self._add).pack(side="left", padx=4)
        ctk.CTkButton(btn_frame, text="Изменить", width=110, command=self._edit).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_frame, text="Удалить", width=110,
            fg_color="#EF4444", hover_color="#DC2626",
            command=self._delete,
        ).pack(side="left", padx=4)

        self._listbox = ctk.CTkScrollableFrame(self)
        self._listbox.pack(fill="both", expand=True, padx=10, pady=5)

        self._refresh()

    def _refresh(self):
        for w in self._listbox.winfo_children():
            w.destroy()
        self._selected = None
        self._buttons = {}
        for t in self._storage.load_templates():
            btn = ctk.CTkButton(
                self._listbox, text=t["name"], anchor="w",
                fg_color="transparent", text_color=("black", "white"),
                hover_color=("gray80", "gray30"),
                command=lambda tid=t["id"]: self._select(tid),
            )
            btn.pack(fill="x", pady=2)
            self._buttons[t["id"]] = btn

    def _select(self, tid):
        if self._selected and self._selected in self._buttons:
            self._buttons[self._selected].configure(fg_color="transparent")
        self._selected = tid
        self._buttons[tid].configure(fg_color=("gray75", "gray25"))

    def _add(self):
        TemplateDialog(self, self._storage, on_save=self._refresh)

    def _edit(self):
        if not self._selected:
            messagebox.showinfo("", "Выберите шаблон")
            return
        template = next((t for t in self._storage.load_templates() if t["id"] == self._selected), None)
        if template:
            TemplateDialog(self, self._storage, template=template, on_save=self._refresh)

    def _delete(self):
        if not self._selected:
            messagebox.showinfo("", "Выберите шаблон")
            return
        if messagebox.askyesno("Удалить", "Удалить шаблон?"):
            templates = [t for t in self._storage.load_templates() if t["id"] != self._selected]
            self._storage.save_templates(templates)
            self._refresh()
