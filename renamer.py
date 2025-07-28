import os, re, shutil, tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinterdnd2 import TkinterDnD, DND_FILES
import ttkbootstrap as tb
from mutagen import File as AudioFile
from PIL import Image, ImageTk

AUDIO = (".mp3", ".flac", ".wav", ".ogg", ".m4a")
IMG = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".gif")
DOC = (".pdf", ".docx", ".txt")
VID = (".mp4", ".mov", ".avi")
ARC = (".zip", ".rar")
SUPPORTED = AUDIO + IMG + DOC + VID + ARC

ILLEGAL, ACCENT, FONT = r'[\\/:*?"<>|]', "#00ffff", ("Consolas", 10)

entries, path_set, target_dir = [], set(), None
sanitize = lambda t: re.sub(r'\s+', ' ', re.sub(ILLEGAL, '', t or '')).strip()
bytes_hr = lambda n: f"{n/1024/1024:.1f} MB" if n else ""

def get_tags(p):
    try:
        a = AudioFile(p, easy=True)
        if not a:
            return None, None, None, None
        dur = a.info.length if a.info else None
        br = a.info.bitrate if a.info else None
        return a.get('artist', [None])[0], a.get('title', [None])[0], dur, br
    except:
        return None, None, None, None

def meta(p, ext):
    size = os.path.getsize(p)
    if ext in AUDIO:
        ar, ti, dur, br = get_tags(p)
        info = f"{int(dur)}s / {br//1000 if br else ''}kbps" if dur else ""
        return ar, ti, info, size
    if ext in IMG:
        try:
            w, h = Image.open(p).size
            info = f"{w}×{h}"
        except:
            info = ""
        return None, None, info, size
    return None, None, "", size

def template_name(art, tit, idx):
    tmpl = tmpl_var.get()
    pfx, sfx = pre_var.get(), suf_var.get()
    base = {"Виконавець – Назва": f"{art} - {tit}",
            "Назва (Виконавець)": f"{tit} ({art})",
            "01 - Назва": f"{idx:02d} - {tit}"}.get(tmpl, f"{art} - {tit}")
    base = pfx + base + sfx
    return base.replace(find_var.get(), repl_var.get())

def insert_row(entry):
    idx = len(entries) - 1
    tree.insert("", "end", iid=idx, values=("✔", idx + 1, entry["type"], entry["original"], entry["new_name"], bytes_hr(entry["size"]), entry["info"]))

def rebuild_indices():
    for new_i, item in enumerate(tree.get_children()):
        tree.item(item, iid=new_i)
        vals = list(tree.item(new_i, "values"))
        vals[1] = new_i + 1
        tree.item(new_i, values=vals)
    global entries
    entries = [entries[int(i)] for i in tree.get_children()]

def update_counter():
    total = len(entries)
    sel = sum(e["selected"].get() for e in entries)
    count_var.set(f"Вибрано: {sel}/{total}")

def toggle(ev):
    if tree.identify_column(ev.x) != "#1":
        return
    item = tree.identify_row(ev.y)
    if not item:
        return
    idx = int(item)
    sel = entries[idx]["selected"]
    sel.set(not sel.get())
    tree.set(idx, "✓", "✔" if sel.get() else "")
    update_counter()

def preview(ev):
    item = tree.identify_row(ev.y)
    if not item:
        return
    idx = int(item)
    e = entries[idx]
    if e["ext"] not in IMG:
        return
    top = tk.Toplevel(root)
    top.title(e["original"])
    img = Image.open(e["path"])
    w, h = img.size
    scale = min(600 / w, 600 / h, 1)
    img = img.resize((int(w * scale), int(h * scale)))
    imgtk = ImageTk.PhotoImage(img)
    tk.Label(top, image=imgtk).pack()
    top.mainloop()

def drop(ev):
    add(root.tk.splitlist(ev.data))

def collect(paths):
    for p in paths:
        if os.path.isdir(p):
            for r, _, fs in os.walk(p):
                for f in fs:
                    yield os.path.join(r, f)
        else:
            yield p

def add(paths=None):
    if not paths:
        paths = filedialog.askopenfilenames()
    start = len(entries) + 1
    for p in collect(paths):
        p = os.path.abspath(p)
        if p in path_set or not os.path.isfile(p):
            continue
        ext = os.path.splitext(p)[1].lower()
        if ext not in SUPPORTED:
            continue
        fn, dirn = os.path.basename(p), os.path.dirname(p)
        art, tit, info, sz = meta(p, ext)
        art, tit = sanitize(art), sanitize(tit)
        if ext in AUDIO:
            if not art:
                art = sanitize(simpledialog.askstring("Автор", fn))
            if not tit:
                tit = sanitize(simpledialog.askstring("Назва", fn))
        else:
            if not tit:
                tit = sanitize(os.path.splitext(fn)[0])
            art = art or ""
        if not tit:
            continue
        new_name = f"{template_name(art, tit, start)}{ext}"
        etype = "🎵" if ext in AUDIO else "🖼" if ext in IMG else "📄" if ext in DOC else "🎬" if ext in VID else "📦"
        entry = {"path": p, "original": fn, "directory": dirn, "new_name": new_name, "ext": ext, "type": etype, "selected": tk.BooleanVar(value=True), "size": sz, "info": info}
        entries.append(entry)
        path_set.add(p)
        insert_row(entry)
        start += 1
    update_counter()

def delete_rows(indices):
    for i in sorted(indices, reverse=True):
        tree.delete(i)
        path_set.remove(entries[i]["path"])
        entries.pop(i)
    rebuild_indices()
    update_counter()

def delete_selected(event=None):
    sel = [int(i) for i in tree.selection()]
    if sel:
        delete_rows(sel)

def clear_all():
    if entries and messagebox.askyesno("Очистити", "Видалити весь список?"):
        tree.delete(*tree.get_children())
        entries.clear()
        path_set.clear()
        update_counter()

def is_duplicate(name, directory, skip_idx):
    for i, e in enumerate(entries):
        if i == skip_idx:
            continue
        if (target_dir or e["directory"]) == directory and e["new_name"].lower() == name.lower():
            return True
    return False

def manual_rename(idx):
    e = entries[idx]
    base_current = os.path.splitext(e["new_name"])[0]
    new_base = sanitize(simpledialog.askstring("Перейменувати", "Нова назва (без розширення):", initialvalue=base_current))
    if not new_base:
        return
    candidate = f"{new_base}{e['ext']}"
    dest_dir = target_dir or e["directory"]
    if is_duplicate(candidate, dest_dir, idx):
        messagebox.showerror("Помилка", "Файл з такою назвою уже буде існувати у цільовій папці.")
        return
    e["new_name"] = candidate
    tree.set(idx, "Нова назва", candidate)

def rename_selected():
    sel = [e for e in entries if e["selected"].get()]
    if not sel:
        messagebox.showwarning("Увага", "Немає вибраних файлів")
        return
    if len(sel) > 100 and not messagebox.askyesno("Підтвердження", f"Перейменувати {len(sel)} файлів?"):
        return
    dest_names = []
    for e in sel:
        dest = target_dir or e["directory"]
        dest_names.append(os.path.join(dest, e["new_name"].lower()))
    if len(dest_names) != len(set(dest_names)):
        messagebox.showerror("Помилка", "У списку вибраних файлів є дублікати імен.")
        return
    for e in sel:
        dest = target_dir or e["directory"]
        os.makedirs(dest, exist_ok=True)
        new_name = e["new_name"]
        full_dest = os.path.join(dest, new_name)
        if os.path.exists(full_dest):
            messagebox.showerror("Помилка", f"Файл {new_name} вже існує.")
            return
        try:
            (shutil.copy2 if copy_var.get() else shutil.move)(e["path"], full_dest)
            log(f"[✓] {e['original']} → {new_name}")
        except Exception as er:
            log(f"[!] {e['original']}: {er}")
    update_counter()

def choose_target():
    global target_dir
    target_dir = filedialog.askdirectory()
    tgt_var.set(target_dir or "")

def log(msg):
    log_box.config(state="normal")
    log_box.insert(tk.END, msg + "\n")
    log_box.config(state="disabled")
    log_box.see(tk.END)

def clear_log():
    log_box.config(state="normal")
    log_box.delete("1.0", tk.END)
    log_box.config(state="disabled")

def about():
    messagebox.showinfo("ℹ️", "ПКМ: контекст-меню (перейменувати, видалити).\n✔ змінюється лише при кліку по стовпцю «✓».\nDelete — видалення рядків.")

root = TkinterDnD.Tk()
root.title("Перейменувач файлів")
root.geometry("1140x730")
tb.Style("darkly")
root.configure(bg="#121212")

top = tk.Frame(root, bg="#121212")
top.pack(pady=6)
tk.Label(top, text="Додай/перетягни файли або папки", font=("Helvetica", 16, "bold"), bg="#121212", fg=ACCENT).grid(row=0, column=0, columnspan=7)
tb.Button(top, text="➕ Додати", bootstyle="info-outline", command=add).grid(row=1, column=0, padx=4)

tmpl_var = tk.StringVar(value="Виконавець – Назва")
tk.Label(top, text="Шаблон:", bg="#121212", fg=ACCENT).grid(row=1, column=1, sticky="e")
ttk.Combobox(top, textvariable=tmpl_var, values=["Виконавець – Назва", "Назва (Виконавець)", "01 - Назва"], width=20).grid(row=1, column=2, padx=4)

pre_var, suf_var, find_var, repl_var = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()
for i, (var, lbl) in enumerate([(pre_var, "префікс"), (suf_var, "суфікс")], start=3):
    tk.Entry(top, textvariable=var, width=8).grid(row=1, column=i)
    tk.Label(top, text=lbl, bg="#121212", fg=ACCENT).grid(row=1, column=i, sticky="e")
for i, (var, lbl) in enumerate([(find_var, "знайти"), (repl_var, "замінити")]):
    tk.Entry(top, textvariable=var, width=10).grid(row=2, column=i)
    tk.Label(top, text=lbl, bg="#121212", fg=ACCENT).grid(row=2, column=i, sticky="e")

copy_var = tk.BooleanVar(value=False)
tb.Checkbutton(top, text="Копіювати, не переміщати", variable=copy_var, bootstyle="info").grid(row=2, column=2, columnspan=2)

tb.Button(top, text="🎯 Цільова папка", bootstyle="secondary-outline", command=choose_target).grid(row=2, column=4)
tgt_var = tk.StringVar()
tk.Entry(top, textvariable=tgt_var, state="readonly", width=24).grid(row=2, column=5, padx=4)

cols = ("✓", "#", "Тип", "Стара назва", "Нова назва", "Розмір", "Інфо")
tree = ttk.Treeview(root, columns=cols, show="headings", height=18, selectmode="extended")
sty = ttk.Style()
sty.configure("Treeview", background="#1e1e1e", foreground=ACCENT, fieldbackground="#1e1e1e", font=FONT)
sty.configure("Treeview.Heading", foreground=ACCENT, font=("Helvetica", 10, "bold"))
for c in cols:
    w = 60 if c in ("✓", "#") else 180 if c == "Розмір" else 260 if c == "Нова назва" else 240
    tree.heading(c, text=c)
    tree.column(c, width=w, anchor="w")
tree.pack(padx=10, pady=6, fill=tk.BOTH, expand=False)
tree.bind("<Button-1>", toggle)
tree.bind("<Double-Button-1>", preview)
tree.bind("<Delete>", delete_selected)
tree.drop_target_register(DND_FILES)
tree.dnd_bind("<<Drop>>", drop)

context_idx = tk.IntVar(value=-1)
row_menu = tk.Menu(root, tearoff=0)
def popup_rename():
    manual_rename(context_idx.get())
row_menu.add_command(label="✏️ Перейменувати", command=popup_rename)
row_menu.add_command(label="❌ Видалити вибране", command=delete_selected)
row_menu.add_separator()
row_menu.add_command(label="🗑 Очистити все", command=clear_all)
empty_menu = tk.Menu(root, tearoff=0)
empty_menu.add_command(label="🗑 Очистити все", command=clear_all)
def context(ev):
    row = tree.identify_row(ev.y)
    if row:
        context_idx.set(int(row))
        tree.selection_set(row)
        row_menu.tk_popup(ev.x_root, ev.y_root)
    else:
        empty_menu.tk_popup(ev.x_root, ev.y_root)
tree.bind("<Button-3>", context)

btn = tk.Frame(root, bg="#121212")
btn.pack(pady=4)
tb.Button(btn, text="🚀 Перейменувати/копіювати", bootstyle="success-outline", command=rename_selected).grid(row=0, column=0, padx=4)
tb.Button(btn, text="🗑 Очистити список", bootstyle="danger-outline", command=clear_all).grid(row=0, column=1, padx=4)
count_var = tk.StringVar(value="Вибрано: 0/0")
tk.Label(btn, textvariable=count_var, fg=ACCENT, bg="#121212").grid(row=0, column=2, padx=8)

tk.Label(root, text="Лог", fg=ACCENT, bg="#121212", font=("Helvetica", 12, "bold")).pack()
log_box = tk.Text(root, height=8, fg=ACCENT, bg="#1e1e1e", font=FONT, state="disabled", wrap=tk.WORD)
log_box.pack(padx=12, pady=4, fill=tk.BOTH, expand=True)
bot = tk.Frame(root, bg="#121212")
bot.pack(pady=5)
tb.Button(bot, text="🧹 Очистити лог", bootstyle="info-outline", command=clear_log).grid(row=0, column=0, padx=5)
tb.Button(bot, text="ℹ️ Про", bootstyle="secondary-outline", command=about).grid(row=0, column=1, padx=5)
tb.Button(bot, text="🚪 Вийти", bootstyle="danger-outline", command=root.quit).grid(row=0, column=2, padx=5)

root.bind("<Delete>", delete_selected)
root.mainloop()
