import customtkinter as ctk


def show_toast(parent, message, color="#4CAF50", duration=3500):
    toast = ctk.CTkToplevel(parent)
    toast.overrideredirect(True)
    toast.attributes("-topmost", True)
    toast.configure(fg_color="#1a1a1a")

    frame = ctk.CTkFrame(toast, fg_color="#2d2d2d", corner_radius=10)
    frame.pack(padx=2, pady=2)
    ctk.CTkLabel(
        frame, text=message, text_color=color, font=ctk.CTkFont(size=13)
    ).pack(padx=20, pady=12)

    toast.update_idletasks()
    w = toast.winfo_reqwidth()
    h = toast.winfo_reqheight()
    sw = toast.winfo_screenwidth()
    sh = toast.winfo_screenheight()
    x = sw - w - 24
    y = sh - h - 64
    toast.geometry(f"{w}x{h}+{x}+{y}")

    toast.after(duration, lambda: toast.destroy() if toast.winfo_exists() else None)
