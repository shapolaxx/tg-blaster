import tkinter as tk


def setup_paste(root):
    """Bind Ctrl+V paste for all tk.Entry and tk.Text descendants of root."""
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
