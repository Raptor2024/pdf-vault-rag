"""Little UI for the PDF -> Markdown pipeline.

- "Add PDFs..." copies chosen PDFs into the PDF Inbox
- The list shows every PDF in the inbox and whether it's converted yet
- "Convert now" launches Convert PDFs.bat in a console window
- Refuses to start a second conversion while one is running

Launch by double-clicking "PDF Converter.bat" (or this file, if .pyw is
associated with pythonw).
"""

import shutil
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

RAG_DIR = Path(__file__).resolve().parent
INBOX = RAG_DIR.parent / "PDF Inbox"
IMPORTS = RAG_DIR.parent / "_pdf_imports"
BAT = RAG_DIR / "Convert PDFs.bat"


def conversion_running() -> bool:
    """True if any pdf_to_md / build_index python process is running."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -match 'pdf_to_md|build_index' }).Count"],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return int(out.stdout.strip() or 0) > 0
    except Exception:
        return False  # if the check fails, don't block the user


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF → Markdown converter")
        self.geometry("560x420")
        INBOX.mkdir(exist_ok=True)

        bar = tk.Frame(self)
        bar.pack(fill="x", padx=10, pady=8)
        tk.Button(bar, text="Add PDFs…", command=self.add_pdfs, width=14).pack(side="left")
        self.convert_btn = tk.Button(bar, text="Convert now", command=self.convert, width=14)
        self.convert_btn.pack(side="left", padx=8)
        tk.Button(bar, text="Refresh", command=self.refresh, width=10).pack(side="left")
        tk.Button(bar, text="Open imports folder", command=lambda: subprocess.Popen(["explorer", str(IMPORTS)]), width=18).pack(side="right")

        self.listbox = tk.Listbox(self, font=("Consolas", 10))
        self.listbox.pack(fill="both", expand=True, padx=10)

        self.status = tk.Label(self, anchor="w", fg="gray")
        self.status.pack(fill="x", padx=10, pady=6)

        self.refresh()
        self.poll()

    def refresh(self):
        self.listbox.delete(0, "end")
        pdfs = sorted(INBOX.glob("*.pdf"))
        for pdf in pdfs:
            done = (IMPORTS / (pdf.stem + ".md")).exists()
            mark = "✓ converted " if done else "• pending   "
            self.listbox.insert("end", f" {mark} {pdf.name}")
            self.listbox.itemconfig("end", fg="green" if done else "black")
        if not pdfs:
            self.listbox.insert("end", "  (inbox is empty — click Add PDFs…)")

    def poll(self):
        if conversion_running():
            self.convert_btn.config(state="disabled")
            self.status.config(text="Conversion running — button re-enables when it finishes.", fg="#b06000")
        else:
            self.convert_btn.config(state="normal")
            self.status.config(text="✓ Ready for next conversion — add PDFs and hit Convert.", fg="#0a7d2c")
            self.refresh()
        self.after(15000, self.poll)

    def add_pdfs(self):
        files = filedialog.askopenfilenames(title="Choose PDFs", filetypes=[("PDF files", "*.pdf")])
        copied = 0
        for f in files:
            src = Path(f)
            dst = INBOX / src.name
            if dst.exists():
                continue
            shutil.copy2(src, dst)
            copied += 1
        if files:
            self.status.config(text=f"Copied {copied} PDF(s) into the inbox.", fg="gray")
        self.refresh()

    def convert(self):
        if conversion_running():
            messagebox.showwarning("Already running", "A conversion is already in progress.\nWait for it to finish first.")
            return
        if not any(INBOX.glob("*.pdf")):
            messagebox.showinfo("Nothing to do", "The inbox has no PDFs. Click Add PDFs… first.")
            return
        subprocess.Popen(["cmd", "/c", "start", "", str(BAT)])
        self.convert_btn.config(state="disabled")
        self.status.config(text="Conversion started in its own window.", fg="#b06000")


if __name__ == "__main__":
    App().mainloop()
