import customtkinter as ctk


class PreviewLabel(ctk.CTkLabel):
    def _update_image(self):
        # CTkLabel no limpia la imagen de Tk cuando recibe image=None.
        # Hay que desconectarla antes de liberar el PhotoImage anterior.
        if self._image is None:
            self._label.configure(image="")
        else:
            super()._update_image()
