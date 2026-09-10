import tkinter as tk

import customtkinter as ctk


class WorkerSearch(ctk.CTkFrame):
    """Buscador con lista flotante de diez filas y desplazamiento vertical."""

    def __init__(self, master, command, search, **kwargs):
        super().__init__(master, fg_color="transparent")
        self.command = command
        self.search = search
        self._labels = []
        self._setting = False
        self._pending = None
        self.variable = tk.StringVar()
        self.entry = ctk.CTkEntry(self, textvariable=self.variable,
                                 placeholder_text="Buscar por nombre completo")
        self.entry.pack(side="left", fill="x", expand=True)
        self.button = ctk.CTkButton(self, text="\u25bc", width=28, command=self._show_all)
        self.button.pack(side="right", padx=(4, 0))
        self.root = self.winfo_toplevel()
        self.popup = tk.Frame(self.root, bd=1, relief="solid")
        self.listbox = tk.Listbox(self.popup, height=10, exportselection=False,
                                 activestyle="dotbox", font=("Segoe UI", 11))
        scrollbar = tk.Scrollbar(self.popup, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.variable.trace_add("write", self._changed)
        self.entry.bind("<Button-1>", lambda event: self._show_all())
        self.entry.bind("<Down>", self._focus_results)
        self.entry.bind("<Return>", self._choose)
        self.entry.bind("<Escape>", lambda event: self.hide())
        self.listbox.bind("<ButtonRelease-1>", self._choose)
        self.listbox.bind("<Return>", self._choose)
        self.listbox.bind("<Escape>", lambda event: self.hide())
        self.root.bind("<Button-1>", self._outside_click, add="+")
        self.root.bind("<Configure>", self._window_changed, add="+")
        self.configure(**kwargs)

    def configure(self, **kwargs):
        kwargs.pop("values", None)
        state = kwargs.pop("state", None)
        if state is not None:
            state = "disabled" if state == "disabled" else "normal"
            self.entry.configure(state=state)
            self.button.configure(state=state)
        if kwargs:
            super().configure(**kwargs)

    def set(self, value):
        self.hide()
        self._setting = True
        try:
            self.variable.set(value)
        finally:
            self._setting = False

    def _changed(self, *_):
        if not self._setting:
            if self._pending is not None:
                self.after_cancel(self._pending)
            self._pending = self.after(150, self._search)

    def _search(self):
        self._pending = None
        self._show(self.variable.get())

    def _show_all(self):
        self.hide()
        self._show("")

    def _show(self, query):
        if self.entry.cget("state") == "disabled":
            return
        self._labels = self.search(query)
        self.listbox.delete(0, "end")
        for label in self._labels:
            self.listbox.insert("end", label)
        if not self._labels:
            self.listbox.insert("end", "Sin coincidencias")
        self.listbox.configure(height=min(10, max(1, len(self._labels))))
        self.listbox.yview_moveto(0)
        self.update_idletasks()
        x = self.winfo_rootx() - self.root.winfo_rootx()
        y = self.winfo_rooty() - self.root.winfo_rooty() + self.winfo_height()
        self.popup.place(x=x, y=y, width=self.winfo_width())
        self.popup.lift()

    def hide(self):
        if self._pending is not None:
            self.after_cancel(self._pending)
            self._pending = None
        self.popup.place_forget()

    def _focus_results(self, event=None):
        if not self.popup.winfo_ismapped():
            self._show(self.variable.get())
        if self._labels:
            self.listbox.focus_set()
            self.listbox.selection_set(0)
            self.listbox.activate(0)
        return "break"

    def _choose(self, event=None):
        if not self.popup.winfo_ismapped() or not self._labels:
            return "break"
        selected = self.listbox.curselection()
        index = selected[0] if selected else 0
        label = self._labels[index]
        self.set(label)
        self.entry.focus_set()
        self.command(label)
        return "break"

    def _outside_click(self, event):
        widget = event.widget
        while widget is not None:
            if widget in (self, self.popup):
                return
            widget = getattr(widget, "master", None)
        self.hide()

    def _window_changed(self, event):
        if event.widget == self.root:
            self.hide()
