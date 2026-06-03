"""
client.py — Auth Service Desktop Client (tkinter)
Подключается к REST API на http://localhost:8000
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import requests

API_BASE_URL = "http://localhost:8000"


def api(method: str, path: str, **kwargs):
    """Обёртка над requests с обработкой ошибок подключения."""
    try:
        resp = getattr(requests, method)(API_BASE_URL + path, **kwargs)
        return resp
    except requests.exceptions.ConnectionError:
        messagebox.showerror(
            "Ошибка подключения",
            "Не удалось подключиться к сервису.\nУбедитесь, что service.py запущен."
        )
        return None
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))
        return None


def show_error(resp):
    """Показать детальную ошибку API по статус-коду."""
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text
    messagebox.showerror("Ошибка " + str(resp.status_code), str(detail))


# ══════════════════════════════════════════════════════════════════════════════
# Вкладка: Пользователи
# ══════════════════════════════════════════════════════════════════════════════

class UsersTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#f5f6fa")
        self._build()

    def _build(self):
        btn_style = {
            "bg": "#4a6fa5", "fg": "white", "relief": tk.FLAT,
            "font": ("Arial", 9), "padx": 10, "pady": 4, "cursor": "hand2"
        }

        action_frame = tk.LabelFrame(
            self, text="Действия", bg="#f5f6fa", font=("Arial", 10, "bold")
        )
        action_frame.pack(fill=tk.X, padx=10, pady=8)

        tk.Button(action_frame, text="➕ Добавить",
                  command=self._open_create, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(action_frame, text="✏️ Изменить по ID",
                  command=self._open_update, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(action_frame, text="🗑 Удалить по ID",
                  command=self._delete, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(action_frame, text="🔍 Получить по ID",
                  command=self._get_by_id, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(action_frame, text="🔄 Обновить список",
                  command=self._load_list, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)

        filter_frame = tk.LabelFrame(
            self, text="Фильтры списка", bg="#f5f6fa", font=("Arial", 10, "bold")
        )
        filter_frame.pack(fill=tk.X, padx=10, pady=4)

        tk.Label(filter_frame, text="Логин (частичный):", bg="#f5f6fa").grid(
            row=0, column=0, padx=6, pady=4, sticky=tk.W
        )
        self.filter_login = tk.Entry(filter_frame, width=20)
        self.filter_login.grid(row=0, column=1, padx=4, pady=4)

        tk.Label(filter_frame, text="Активен:", bg="#f5f6fa").grid(
            row=0, column=2, padx=6, pady=4, sticky=tk.W
        )
        self.filter_active = ttk.Combobox(
            filter_frame, values=["", "true", "false"], width=8, state="readonly"
        )
        self.filter_active.grid(row=0, column=3, padx=4, pady=4)
        self.filter_active.set("")

        tk.Button(filter_frame, text="Применить",
                  command=self._load_list, **btn_style).grid(row=0, column=4, padx=8, pady=4)

        cols = ("id", "login", "is_active", "created_at", "updated_at")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=15)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=160)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=6)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y, pady=6)

        self._load_list()

    def _load_list(self):
        params = {}
        if self.filter_login.get().strip():
            params["login"] = self.filter_login.get().strip()
        active = self.filter_active.get()
        if active:
            params["is_active"] = active
        resp = api("get", "/users/", params=params)
        if resp is None:
            return
        if resp.status_code == 200:
            self.tree.delete(*self.tree.get_children())
            for u in resp.json():
                self.tree.insert("", tk.END, values=(
                    u["id"], u["login"], u["is_active"],
                    u["created_at"][:19], u["updated_at"][:19]
                ))
        else:
            show_error(resp)

    def _selected_id(self):
        sel = self.tree.selection()
        if sel:
            return self.tree.item(sel[0])["values"][0]
        return None

    def _open_create(self):
        dlg = tk.Toplevel(self)
        dlg.title("Добавить пользователя")
        dlg.resizable(False, False)
        dlg.configure(bg="#f5f6fa")

        tk.Label(dlg, text="Логин:", bg="#f5f6fa").grid(
            row=0, column=0, padx=10, pady=6, sticky=tk.W
        )
        e_login = tk.Entry(dlg, width=28)
        e_login.grid(row=0, column=1, padx=10, pady=6)

        tk.Label(dlg, text="Пароль:", bg="#f5f6fa").grid(
            row=1, column=0, padx=10, pady=6, sticky=tk.W
        )
        e_pass = tk.Entry(dlg, width=28, show="*")
        e_pass.grid(row=1, column=1, padx=10, pady=6)

        def submit():
            login = e_login.get().strip()
            password = e_pass.get()
            if not login or not password:
                messagebox.showwarning("Внимание", "Заполните все поля", parent=dlg)
                return
            resp = api("post", "/users/", json={"login": login, "password": password})
            if resp is None:
                return
            if resp.status_code == 201:
                messagebox.showinfo(
                    "Успех", "Пользователь создан, ID=" + str(resp.json()["id"]), parent=dlg
                )
                dlg.destroy()
                self._load_list()
            elif resp.status_code == 409:
                messagebox.showerror("Конфликт", "Логин уже занят", parent=dlg)
            elif resp.status_code == 400:
                messagebox.showerror("Ошибка валидации", str(resp.json()), parent=dlg)
            else:
                show_error(resp)

        tk.Button(dlg, text="Создать", command=submit,
                  bg="#4a6fa5", fg="white", relief=tk.FLAT, padx=12).grid(
            row=2, column=0, columnspan=2, pady=10
        )

    def _open_update(self):
        uid = self._selected_id()
        dlg = tk.Toplevel(self)
        dlg.title("Изменить пользователя")
        dlg.resizable(False, False)
        dlg.configure(bg="#f5f6fa")

        tk.Label(dlg, text="ID пользователя:", bg="#f5f6fa").grid(
            row=0, column=0, padx=10, pady=6, sticky=tk.W
        )
        e_id = tk.Entry(dlg, width=12)
        e_id.grid(row=0, column=1, padx=10, pady=6, sticky=tk.W)
        if uid:
            e_id.insert(0, str(uid))

        tk.Label(dlg, text="Новый логин:", bg="#f5f6fa").grid(
            row=1, column=0, padx=10, pady=6, sticky=tk.W
        )
        e_login = tk.Entry(dlg, width=28)
        e_login.grid(row=1, column=1, padx=10, pady=6)

        tk.Label(dlg, text="Новый пароль:", bg="#f5f6fa").grid(
            row=2, column=0, padx=10, pady=6, sticky=tk.W
        )
        e_pass = tk.Entry(dlg, width=28, show="*")
        e_pass.grid(row=2, column=1, padx=10, pady=6)

        tk.Label(
            dlg, text="(оставьте пустыми, чтобы не менять)",
            bg="#f5f6fa", font=("Arial", 8), fg="#888"
        ).grid(row=3, column=0, columnspan=2)

        def submit():
            uid_val = e_id.get().strip()
            if not uid_val.isdigit():
                messagebox.showwarning("Внимание", "Введите корректный ID", parent=dlg)
                return
            body = {}
            if e_login.get().strip():
                body["login"] = e_login.get().strip()
            if e_pass.get():
                body["password"] = e_pass.get()
            if not body:
                messagebox.showwarning("Внимание", "Нет данных для обновления", parent=dlg)
                return
            resp = api("put", "/users/" + uid_val, json=body)
            if resp is None:
                return
            if resp.status_code == 200:
                messagebox.showinfo("Успех", "Пользователь обновлён", parent=dlg)
                dlg.destroy()
                self._load_list()
            elif resp.status_code == 404:
                messagebox.showerror("Не найдено", "Пользователь не найден", parent=dlg)
            elif resp.status_code == 409:
                messagebox.showerror("Конфликт", "Логин уже занят", parent=dlg)
            elif resp.status_code == 400:
                messagebox.showerror("Ошибка валидации", str(resp.json()), parent=dlg)
            else:
                show_error(resp)

        tk.Button(dlg, text="Сохранить", command=submit,
                  bg="#4a6fa5", fg="white", relief=tk.FLAT, padx=12).grid(
            row=4, column=0, columnspan=2, pady=10
        )

    def _delete(self):
        uid = self._selected_id()
        dlg = tk.Toplevel(self)
        dlg.title("Удалить пользователя")
        dlg.resizable(False, False)
        dlg.configure(bg="#f5f6fa")

        tk.Label(dlg, text="ID пользователя:", bg="#f5f6fa").grid(
            row=0, column=0, padx=10, pady=8, sticky=tk.W
        )
        e_id = tk.Entry(dlg, width=12)
        e_id.grid(row=0, column=1, padx=10, pady=8)
        if uid:
            e_id.insert(0, str(uid))

        def submit():
            uid_val = e_id.get().strip()
            if not uid_val.isdigit():
                messagebox.showwarning("Внимание", "Введите корректный ID", parent=dlg)
                return
            if not messagebox.askyesno(
                "Подтверждение", "Удалить пользователя ID=" + uid_val + "?", parent=dlg
            ):
                return
            resp = api("delete", "/users/" + uid_val)
            if resp is None:
                return
            if resp.status_code == 200 and resp.json().get("success"):
                messagebox.showinfo("Успех", "Пользователь удалён", parent=dlg)
                dlg.destroy()
                self._load_list()
            else:
                messagebox.showwarning("Не найдено", "Пользователь не найден", parent=dlg)

        tk.Button(dlg, text="Удалить", command=submit,
                  bg="#c0392b", fg="white", relief=tk.FLAT, padx=12).grid(
            row=1, column=0, columnspan=2, pady=10
        )

    def _get_by_id(self):
        uid = self._selected_id()
        dlg = tk.Toplevel(self)
        dlg.title("Получить пользователя по ID")
        dlg.resizable(False, False)
        dlg.configure(bg="#f5f6fa")

        tk.Label(dlg, text="ID пользователя:", bg="#f5f6fa").grid(
            row=0, column=0, padx=10, pady=8, sticky=tk.W
        )
        e_id = tk.Entry(dlg, width=12)
        e_id.grid(row=0, column=1, padx=10, pady=8)
        if uid:
            e_id.insert(0, str(uid))

        result_text = tk.Text(dlg, height=7, width=50, state=tk.DISABLED, bg="#fafafa")
        result_text.grid(row=2, column=0, columnspan=2, padx=10, pady=6)

        def submit():
            uid_val = e_id.get().strip()
            if not uid_val.isdigit():
                messagebox.showwarning("Внимание", "Введите корректный ID", parent=dlg)
                return
            resp = api("get", "/users/" + uid_val)
            if resp is None:
                return
            result_text.config(state=tk.NORMAL)
            result_text.delete("1.0", tk.END)
            if resp.status_code == 200:
                u = resp.json()
                result_text.insert(
                    tk.END,
                    "ID:         " + str(u["id"]) + "\n" +
                    "Логин:      " + u["login"] + "\n" +
                    "Активен:    " + str(u["is_active"]) + "\n" +
                    "Создан:     " + u["created_at"][:19] + "\n" +
                    "Изменён:    " + u["updated_at"][:19]
                )
            elif resp.status_code == 404:
                result_text.insert(tk.END, "Пользователь не найден")
            else:
                result_text.insert(tk.END, "Ошибка " + str(resp.status_code) + ":\n" + resp.text)
            result_text.config(state=tk.DISABLED)

        tk.Button(dlg, text="Найти", command=submit,
                  bg="#4a6fa5", fg="white", relief=tk.FLAT, padx=12).grid(
            row=1, column=0, columnspan=2, pady=6
        )


# ══════════════════════════════════════════════════════════════════════════════
# Вкладка: Аутентификация
# ══════════════════════════════════════════════════════════════════════════════

class AuthTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#f5f6fa")
        self._build()

    def _build(self):
        login_frame = tk.LabelFrame(
            self, text="Вход (получить JWT-токен)", bg="#f5f6fa", font=("Arial", 10, "bold")
        )
        login_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(login_frame, text="Логин:", bg="#f5f6fa").grid(
            row=0, column=0, padx=8, pady=6, sticky=tk.W
        )
        self.e_login = tk.Entry(login_frame, width=28)
        self.e_login.grid(row=0, column=1, padx=8, pady=6)

        tk.Label(login_frame, text="Пароль:", bg="#f5f6fa").grid(
            row=1, column=0, padx=8, pady=6, sticky=tk.W
        )
        self.e_pass = tk.Entry(login_frame, width=28, show="*")
        self.e_pass.grid(row=1, column=1, padx=8, pady=6)

        self.token_var = tk.StringVar(value="—")
        tk.Label(login_frame, text="Токен:", bg="#f5f6fa").grid(
            row=2, column=0, padx=8, pady=6, sticky=tk.W
        )
        tk.Entry(login_frame, textvariable=self.token_var, width=55,
                 state="readonly", bg="#eef").grid(row=2, column=1, padx=8, pady=6)

        tk.Button(login_frame, text="Войти", command=self._login,
                  bg="#4a6fa5", fg="white", relief=tk.FLAT, padx=12).grid(
            row=3, column=0, columnspan=2, pady=8
        )

        reset_frame = tk.LabelFrame(
            self, text="Сброс пароля", bg="#f5f6fa", font=("Arial", 10, "bold")
        )
        reset_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(
            reset_frame, text="Шаг 1 — Запросить токен сброса",
            bg="#f5f6fa", font=("Arial", 9, "italic")
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=8)

        tk.Label(reset_frame, text="Логин:", bg="#f5f6fa").grid(
            row=1, column=0, padx=8, pady=4, sticky=tk.W
        )
        self.e_reset_login = tk.Entry(reset_frame, width=28)
        self.e_reset_login.grid(row=1, column=1, padx=8, pady=4)

        self.reset_token_var = tk.StringVar(value="")
        tk.Label(reset_frame, text="Полученный токен:", bg="#f5f6fa").grid(
            row=2, column=0, padx=8, pady=4, sticky=tk.W
        )
        tk.Entry(reset_frame, textvariable=self.reset_token_var, width=55,
                 state="readonly", bg="#eef").grid(row=2, column=1, padx=8, pady=4)

        tk.Button(reset_frame, text="Запросить токен", command=self._request_reset,
                  bg="#4a6fa5", fg="white", relief=tk.FLAT, padx=10).grid(
            row=3, column=0, columnspan=2, pady=6
        )

        ttk.Separator(reset_frame, orient=tk.HORIZONTAL).grid(
            row=4, column=0, columnspan=2, sticky=tk.EW, pady=6
        )

        tk.Label(
            reset_frame, text="Шаг 2 — Применить новый пароль",
            bg="#f5f6fa", font=("Arial", 9, "italic")
        ).grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=8)

        tk.Label(reset_frame, text="Токен сброса:", bg="#f5f6fa").grid(
            row=6, column=0, padx=8, pady=4, sticky=tk.W
        )
        self.e_confirm_token = tk.Entry(reset_frame, width=55)
        self.e_confirm_token.grid(row=6, column=1, padx=8, pady=4)

        tk.Label(reset_frame, text="Новый пароль:", bg="#f5f6fa").grid(
            row=7, column=0, padx=8, pady=4, sticky=tk.W
        )
        self.e_new_pass = tk.Entry(reset_frame, width=28, show="*")
        self.e_new_pass.grid(row=7, column=1, padx=8, pady=4)

        tk.Button(reset_frame, text="Применить", command=self._confirm_reset,
                  bg="#4a6fa5", fg="white", relief=tk.FLAT, padx=10).grid(
            row=8, column=0, columnspan=2, pady=6
        )

    def _login(self):
        login = self.e_login.get().strip()
        password = self.e_pass.get()
        if not login or not password:
            messagebox.showwarning("Внимание", "Введите логин и пароль")
            return
        resp = api("post", "/auth/login", json={"login": login, "password": password})
        if resp is None:
            return
        if resp.status_code == 200:
            self.token_var.set(resp.json().get("access_token", ""))
            messagebox.showinfo("Успех", "Вход выполнен! JWT-токен получен.")
        elif resp.status_code == 401:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
        elif resp.status_code == 403:
            messagebox.showerror("Ошибка", "Аккаунт отключён")
        elif resp.status_code == 400:
            messagebox.showerror("Ошибка валидации", str(resp.json()))
        else:
            show_error(resp)

    def _request_reset(self):
        login = self.e_reset_login.get().strip()
        if not login:
            messagebox.showwarning("Внимание", "Введите логин")
            return
        resp = api("post", "/auth/reset-password/request", json={"login": login})
        if resp is None:
            return
        if resp.status_code == 200:
            token = resp.json().get("token", "")
            self.reset_token_var.set(token)
            self.e_confirm_token.delete(0, tk.END)
            self.e_confirm_token.insert(0, token)
            messagebox.showinfo("Успех", "Токен сброса создан и подставлен в поле ниже.")
        elif resp.status_code == 404:
            messagebox.showerror("Не найдено", "Пользователь не найден")
        elif resp.status_code == 409:
            messagebox.showerror("Конфликт", "Активный токен уже существует для этого пользователя")
        else:
            show_error(resp)

    def _confirm_reset(self):
        token = self.e_confirm_token.get().strip()
        new_pass = self.e_new_pass.get()
        if not token or not new_pass:
            messagebox.showwarning("Внимание", "Заполните токен и новый пароль")
            return
        resp = api(
            "post", "/auth/reset-password/confirm",
            json={"token": token, "new_password": new_pass}
        )
        if resp is None:
            return
        if resp.status_code == 200:
            messagebox.showinfo("Успех", "Пароль изменён для: " + resp.json()["login"])
        elif resp.status_code == 400:
            # Детализируем: Token already used vs Token expired
            try:
                detail = resp.json().get("detail", "")
            except Exception:
                detail = resp.text
            messagebox.showerror("Ошибка 400", str(detail))
        elif resp.status_code == 404:
            messagebox.showerror("Не найдено", "Токен не найден")
        else:
            show_error(resp)


# ══════════════════════════════════════════════════════════════════════════════
# Вкладка: Токены сброса пароля
# ══════════════════════════════════════════════════════════════════════════════

class ResetTokensTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#f5f6fa")
        self._build()

    def _build(self):
        btn_style = {
            "bg": "#4a6fa5", "fg": "white", "relief": tk.FLAT,
            "font": ("Arial", 9), "padx": 10, "pady": 4, "cursor": "hand2"
        }

        action_frame = tk.LabelFrame(
            self, text="Действия", bg="#f5f6fa", font=("Arial", 10, "bold")
        )
        action_frame.pack(fill=tk.X, padx=10, pady=8)

        tk.Button(action_frame, text="➕ Создать токен",
                  command=self._open_create, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(action_frame, text="✏️ Изменить по ID",
                  command=self._open_update, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(action_frame, text="🗑 Удалить по ID",
                  command=self._delete, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(action_frame, text="🔍 Получить по ID",
                  command=self._get_by_id, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Button(action_frame, text="🔄 Обновить список",
                  command=self._load_list, **btn_style).pack(side=tk.LEFT, padx=4, pady=6)

        filter_frame = tk.LabelFrame(
            self, text="Фильтры", bg="#f5f6fa", font=("Arial", 10, "bold")
        )
        filter_frame.pack(fill=tk.X, padx=10, pady=4)

        tk.Label(filter_frame, text="user_id (int):", bg="#f5f6fa").grid(
            row=0, column=0, padx=6, pady=4, sticky=tk.W
        )
        self.filter_uid = tk.Entry(filter_frame, width=10)
        self.filter_uid.grid(row=0, column=1, padx=4, pady=4)

        tk.Label(filter_frame, text="Использован:", bg="#f5f6fa").grid(
            row=0, column=2, padx=6, pady=4, sticky=tk.W
        )
        self.filter_used = ttk.Combobox(
            filter_frame, values=["", "true", "false"], width=8, state="readonly"
        )
        self.filter_used.grid(row=0, column=3, padx=4, pady=4)
        self.filter_used.set("")

        tk.Button(filter_frame, text="Применить",
                  command=self._load_list, **btn_style).grid(row=0, column=4, padx=8, pady=4)

        cols = ("id", "user_id", "token", "expires_at", "is_used", "created_at")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        widths = {
            "id": 40, "user_id": 70, "token": 240,
            "expires_at": 150, "is_used": 70, "created_at": 150
        }
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths.get(col, 120))
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=6)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y, pady=6)

        self._load_list()

    def _load_list(self):
        params = {}
        uid = self.filter_uid.get().strip()
        if uid.isdigit():
            params["user_id"] = int(uid)
        used = self.filter_used.get()
        if used:
            params["is_used"] = used
        resp = api("get", "/reset-tokens/", params=params)
        if resp is None:
            return
        if resp.status_code == 200:
            self.tree.delete(*self.tree.get_children())
            for t in resp.json():
                token_short = t["token"][:40] + ("..." if len(t["token"]) > 40 else "")
                self.tree.insert("", tk.END, values=(
                    t["id"], t["user_id"], token_short,
                    t["expires_at"][:19], t["is_used"], t["created_at"][:19]
                ))
        else:
            show_error(resp)

    def _selected_id(self):
        sel = self.tree.selection()
        if sel:
            return self.tree.item(sel[0])["values"][0]
        return None

    def _open_create(self):
        dlg = tk.Toplevel(self)
        dlg.title("Создать токен сброса пароля")
        dlg.resizable(False, False)
        dlg.configure(bg="#f5f6fa")

        tk.Label(dlg, text="ID пользователя (user_id):", bg="#f5f6fa").grid(
            row=0, column=0, padx=10, pady=6, sticky=tk.W
        )
        e_uid = tk.Entry(dlg, width=12)
        e_uid.grid(row=0, column=1, padx=10, pady=6)

        tk.Label(dlg, text="Токен (или пусто = авто):", bg="#f5f6fa").grid(
            row=1, column=0, padx=10, pady=6, sticky=tk.W
        )
        e_token = tk.Entry(dlg, width=40)
        e_token.grid(row=1, column=1, padx=10, pady=6)

        default_expires = (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        tk.Label(dlg, text="Срок действия (UTC):", bg="#f5f6fa").grid(
            row=2, column=0, padx=10, pady=6, sticky=tk.W
        )
        e_expires = tk.Entry(dlg, width=22)
        e_expires.grid(row=2, column=1, padx=10, pady=6)
        e_expires.insert(0, default_expires)

        tk.Label(
            dlg, text="Формат: YYYY-MM-DD HH:MM:SS (UTC)",
            bg="#f5f6fa", font=("Arial", 8), fg="#888"
        ).grid(row=3, column=0, columnspan=2)

        def submit():
            uid_val = e_uid.get().strip()
            if not uid_val.isdigit():
                messagebox.showwarning("Внимание", "Введите числовой ID пользователя", parent=dlg)
                return

            import secrets as _s
            token_val = e_token.get().strip() or _s.token_urlsafe(32)

            expires_str = e_expires.get().strip()
            try:
                datetime.strptime(expires_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                messagebox.showwarning("Внимание", "Неверный формат даты", parent=dlg)
                return

            resp = api("post", "/reset-tokens/", json={
                "user_id": int(uid_val),
                "token": token_val,
                "expires_at": expires_str.replace(" ", "T"),
            })
            if resp is None:
                return
            if resp.status_code == 201:
                messagebox.showinfo(
                    "Успех", "Токен создан, ID=" + str(resp.json()["id"]), parent=dlg
                )
                dlg.destroy()
                self._load_list()
            elif resp.status_code == 404:
                messagebox.showerror("Не найдено", "Пользователь не найден", parent=dlg)
            elif resp.status_code == 409:
                messagebox.showerror("Конфликт", "Такой токен уже существует", parent=dlg)
            elif resp.status_code == 400:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text
                messagebox.showerror("Ошибка 400", str(detail), parent=dlg)
            else:
                show_error(resp)

        tk.Button(dlg, text="Создать", command=submit,
                  bg="#4a6fa5", fg="white", relief=tk.FLAT, padx=12).grid(
            row=4, column=0, columnspan=2, pady=10
        )

    def _open_update(self):
        tid = self._selected_id()
        dlg = tk.Toplevel(self)
        dlg.title("Изменить токен")
        dlg.resizable(False, False)
        dlg.configure(bg="#f5f6fa")

        tk.Label(dlg, text="ID токена:", bg="#f5f6fa").grid(
            row=0, column=0, padx=10, pady=6, sticky=tk.W
        )
        e_id = tk.Entry(dlg, width=12)
        e_id.grid(row=0, column=1, padx=10, pady=6)
        if tid:
            e_id.insert(0, str(tid))

        tk.Label(dlg, text="Отметить как использованный:", bg="#f5f6fa").grid(
            row=1, column=0, padx=10, pady=6, sticky=tk.W
        )
        used_var = tk.BooleanVar(value=True)
        tk.Checkbutton(dlg, variable=used_var, bg="#f5f6fa").grid(
            row=1, column=1, padx=10, pady=6, sticky=tk.W
        )

        def submit():
            tid_val = e_id.get().strip()
            if not tid_val.isdigit():
                messagebox.showwarning("Внимание", "Введите корректный ID", parent=dlg)
                return
            resp = api("put", "/reset-tokens/" + tid_val, json={"is_used": used_var.get()})
            if resp is None:
                return
            if resp.status_code == 200:
                messagebox.showinfo("Успех", "Токен обновлён", parent=dlg)
                dlg.destroy()
                self._load_list()
            elif resp.status_code == 404:
                messagebox.showerror("Не найдено", "Токен не найден", parent=dlg)
            elif resp.status_code == 400:
                messagebox.showerror("Ошибка валидации", str(resp.json()), parent=dlg)
            else:
                show_error(resp)

        tk.Button(dlg, text="Сохранить", command=submit,
                  bg="#4a6fa5", fg="white", relief=tk.FLAT, padx=12).grid(
            row=2, column=0, columnspan=2, pady=10
        )

    def _delete(self):
        tid = self._selected_id()
        dlg = tk.Toplevel(self)
        dlg.title("Удалить токен")
        dlg.resizable(False, False)
        dlg.configure(bg="#f5f6fa")

        tk.Label(dlg, text="ID токена:", bg="#f5f6fa").grid(
            row=0, column=0, padx=10, pady=8, sticky=tk.W
        )
        e_id = tk.Entry(dlg, width=12)
        e_id.grid(row=0, column=1, padx=10, pady=8)
        if tid:
            e_id.insert(0, str(tid))

        def submit():
            tid_val = e_id.get().strip()
            if not tid_val.isdigit():
                messagebox.showwarning("Внимание", "Введите корректный ID", parent=dlg)
                return
            if not messagebox.askyesno(
                "Подтверждение", "Удалить токен ID=" + tid_val + "?", parent=dlg
            ):
                return
            resp = api("delete", "/reset-tokens/" + tid_val)
            if resp is None:
                return
            if resp.status_code == 200 and resp.json().get("success"):
                messagebox.showinfo("Успех", "Токен удалён", parent=dlg)
                dlg.destroy()
                self._load_list()
            else:
                messagebox.showwarning("Не найдено", "Токен не найден", parent=dlg)

        tk.Button(dlg, text="Удалить", command=submit,
                  bg="#c0392b", fg="white", relief=tk.FLAT, padx=12).grid(
            row=1, column=0, columnspan=2, pady=10
        )

    def _get_by_id(self):
        tid = self._selected_id()
        dlg = tk.Toplevel(self)
        dlg.title("Получить токен по ID")
        dlg.resizable(False, False)
        dlg.configure(bg="#f5f6fa")

        tk.Label(dlg, text="ID токена:", bg="#f5f6fa").grid(
            row=0, column=0, padx=10, pady=8, sticky=tk.W
        )
        e_id = tk.Entry(dlg, width=12)
        e_id.grid(row=0, column=1, padx=10, pady=8)
        if tid:
            e_id.insert(0, str(tid))

        result_text = tk.Text(dlg, height=8, width=55, state=tk.DISABLED, bg="#fafafa")
        result_text.grid(row=2, column=0, columnspan=2, padx=10, pady=6)

        def submit():
            tid_val = e_id.get().strip()
            if not tid_val.isdigit():
                messagebox.showwarning("Внимание", "Введите корректный ID", parent=dlg)
                return
            resp = api("get", "/reset-tokens/" + tid_val)
            if resp is None:
                return
            result_text.config(state=tk.NORMAL)
            result_text.delete("1.0", tk.END)
            if resp.status_code == 200:
                t = resp.json()
                result_text.insert(
                    tk.END,
                    "ID:          " + str(t["id"]) + "\n" +
                    "user_id:     " + str(t["user_id"]) + "\n" +
                    "token:       " + t["token"] + "\n" +
                    "expires_at:  " + t["expires_at"][:19] + "\n" +
                    "is_used:     " + str(t["is_used"]) + "\n" +
                    "created_at:  " + t["created_at"][:19]
                )
            elif resp.status_code == 404:
                result_text.insert(tk.END, "Токен не найден")
            else:
                result_text.insert(
                    tk.END, "Ошибка " + str(resp.status_code) + ":\n" + resp.text
                )
            result_text.config(state=tk.DISABLED)

        tk.Button(dlg, text="Найти", command=submit,
                  bg="#4a6fa5", fg="white", relief=tk.FLAT, padx=12).grid(
            row=1, column=0, columnspan=2, pady=6
        )


# ══════════════════════════════════════════════════════════════════════════════
# Главное окно
# ══════════════════════════════════════════════════════════════════════════════

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Auth Service — клиентское приложение")
        self.root.geometry("960x640")
        self.root.configure(bg="#f5f6fa")
        self._build_header()
        self._build_tabs()

    def _build_header(self):
        header = tk.Frame(self.root, bg="#4a6fa5", height=48)
        header.pack(fill=tk.X)
        tk.Label(
            header, text="🔐  Auth Service  |  S1",
            bg="#4a6fa5", fg="white", font=("Arial", 14, "bold")
        ).pack(side=tk.LEFT, padx=16, pady=10)
        tk.Label(
            header, text="API: " + API_BASE_URL,
            bg="#4a6fa5", fg="#cce0ff", font=("Arial", 9)
        ).pack(side=tk.RIGHT, padx=16)

    def _build_tabs(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        nb.add(UsersTab(nb), text="👤 Пользователи")
        nb.add(AuthTab(nb), text="🔑 Аутентификация")
        nb.add(ResetTokensTab(nb), text="🗝 Токены сброса")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()