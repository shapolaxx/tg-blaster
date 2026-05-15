import tkinter as tk


def _make_entry_paste(inner: tk.Entry):
    def _paste(e):
        try:
            text = inner.clipboard_get()
        except Exception:
            return "break"
        try:
            inner.delete("sel.first", "sel.last")
        except Exception:
            pass
        inner.insert(inner.index("insert"), text)
        return "break"
    return _paste


def _make_text_paste(inner: tk.Text):
    def _paste(e):
        try:
            text = inner.clipboard_get()
        except Exception:
            return "break"
        try:
            inner.delete("sel.first", "sel.last")
        except Exception:
            pass
        inner.insert("insert", text)
        return "break"
    return _paste


def fix_entry(ctk_entry):
    """Bind Ctrl+V directly on the inner tk.Entry of a CTkEntry."""
    inner = getattr(ctk_entry, "_entry", None)
    if inner is not None:
        inner.bind("<Control-v>", _make_entry_paste(inner))


def fix_textbox(ctk_textbox):
    """Bind Ctrl+V directly on the inner tk.Text of a CTkTextbox."""
    inner = getattr(ctk_textbox, "_textbox", None)
    if inner is not None:
        inner.bind("<Control-v>", _make_text_paste(inner))


def setup_paste(root):
    """Fallback bind_all for windows without individual widget fixes."""
    def _paste(e):
        w = e.widget
        try:
            text = w.clipboard_get()
        except tk.TclError:
            return "break"
        if isinstance(w, tk.Text):
            if str(w.cget("state")) == "disabled":
                return "break"
            try:
                w.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            w.insert("insert", text)
        elif isinstance(w, tk.Entry):
            if str(w.cget("state")) in ("disabled", "readonly"):
                return "break"
            try:
                w.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
            w.insert(w.index("insert"), text)
        return "break"

    root.bind_all("<Control-v>", _paste)
