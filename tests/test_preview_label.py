import gc
import unittest

import customtkinter as ctk
from PIL import Image

from ui.preview_label import PreviewLabel


class PreviewLabelTest(unittest.TestCase):
    def test_clear_release_and_show_another_preview(self):
        root = ctk.CTk()
        root.withdraw()
        try:
            label = PreviewLabel(root)
            label.pack()
            for color in ("red", "blue", "green"):
                preview = ctk.CTkImage(Image.new("RGB", (30, 40), color), size=(30, 40))
                label.configure(image=preview, text="")
                root.update_idletasks()
                label.configure(image=None, text="Sin vista previa")
                del preview
                gc.collect()
                self.assertEqual(str(label._label.cget("image")), "")
            label.configure(image=ctk.CTkImage(Image.new("RGB", (30, 40))), text="")
            root.update_idletasks()
        finally:
            root.destroy()
