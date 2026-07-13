"""Little UI for the PDF -> Markdown pipeline.

- "Add PDFs..." copies chosen PDFs into the PDF Inbox
- The list shows every PDF in the inbox and whether it's converted yet
- "Convert now" launches Convert PDFs.bat in a console window
- "Stop" kills a running conversion (and its console window) after confirming
- Refuses to start a second conversion while one is running
- Opens with a fresh, current view every time (no stale state carried over)

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
IMPORTS = RAG_DIR.parent / "Article VI Book" / "_pdf_imports"
BAT = RAG_DIR / "Convert PDFs.bat"

# Matches the conversion worker processes and the console window running the
# batch file - but NOT this UI (its launcher is "PDF Converter.bat", which does
# not match 'Convert PDFs').
_FIND_JOBS = (
    "Get-CimInstance Win32_Process | Where-Object { "
    "($_.Name -eq 'python.exe' -and $_.CommandLine -match 'pdf_to_md|build_index') -or "
    "($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Convert PDFs') }"
)


def conversion_running() -> str | None:
    """If a conversion/index job is running, describe it; else None."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -match 'pdf_to_md|build_index' } | "
             "Select-Object -First 1 -ExpandProperty CommandLine)"],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        cmd = out.stdout.strip()
        if not cmd:
            return None
        if "build_index" in cmd:
            return "updating search index"
        # last quoted or bare argument = the target pdf/folder
        args = [a.strip('"') for a in cmd.replace("'", '"').split('"') if a.strip()]
        target = Path(args[-1]).name if args else ""
        big = " (big-file mode)" if "pdf_to_md_big" in cmd else ""
        return f"converting {target}{big}" if target else "converting"
    except Exception:
        return None  # if the check fails, don't block the user


def stop_conversion() -> int:
    """Kill the conversion worker(s) and their console window. Returns how
    many processes were told to stop (0 = nothing was running)."""
    script = (
        "$ps = @(" + _FIND_JOBS + "); "
        "foreach ($p in $ps) { taskkill /PID $($p.ProcessId) /T /F | Out-Null }; "
        "Write-Output $ps.Count"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return int(out.stdout.strip() or 0)
    except Exception:
        return 0


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
        self.stop_btn = tk.Button(bar, text="Stop", command=self.stop, width=8,
                                  state="disabled", fg="#8f1d1d")
        self.stop_btn.pack(side="left")
        tk.Button(bar, text="Refresh", command=self.refresh, width=10).pack(side="left", padx=8)
        tk.Button(bar, text="Open imports folder", command=lambda: subprocess.Popen(["explorer", str(IMPORTS)]), width=18).pack(side="right")

        self.listbox = tk.Listbox(self, font=("Consolas", 10))
        self.listbox.pack(fill="both", expand=True, padx=10)

        self.status = tk.Label(self, anchor="w", fg="gray")
        self.status.pack(fill="x", padx=10, pady=6)

        # Fresh view on every open: rebuild the list and check the real process
        # state right now, instead of trusting anything left over.
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
            self.listbox.insert("end", "  (inbox is empty: click Add PDFs...)")

    def poll(self):
        job = conversion_running()
        if job:
            self.convert_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.status.config(text=f"⏳ Working: {job}. Stop cancels it; the button re-enables when done.", fg="#b06000")
        else:
            self.convert_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.status.config(text="✓ Ready for next conversion. Add PDFs and hit Convert.", fg="#0a7d2c")
            self.refresh()
        self.after(5000, self.poll)

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
        if conversion_running() is not None:
            messagebox.showwarning("Already running", "A conversion is already in progress.\nWait for it to finish, or press Stop first.")
            return
        if not any(INBOX.glob("*.pdf")):
            messagebox.showinfo("Nothing to do", "The inbox has no PDFs. Click Add PDFs… first.")
            return
        subprocess.Popen(["cmd", "/c", "start", "", str(BAT)])
        self.convert_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.config(text="Conversion started in its own window.", fg="#b06000")

    def stop(self):
        job = conversion_running()
        if job is None:
            self.status.config(text="Nothing is running.", fg="gray")
            self.stop_btn.config(state="disabled")
            return
        if not messagebox.askyesno(
            "Stop conversion?",
            f"Currently {job}.\n\nStop it? The PDF being converted stays in the "
            f"inbox unchanged - you can convert it again later.",
        ):
            return
        n = stop_conversion()
        if n:
            self.status.config(text=f"Stopped ({n} process(es) ended). The inbox PDFs are untouched.", fg="#8f1d1d")
        else:
            self.status.config(text="Nothing was running by the time Stop ran.", fg="gray")
        self.stop_btn.config(state="disabled")
        self.convert_btn.config(state="normal")
        self.refresh()


if __name__ == "__main__":
    App().mainloop()
