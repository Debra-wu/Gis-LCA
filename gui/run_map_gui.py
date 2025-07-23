
from main_window import GreenAmmoniaApp
import tkinter as tk

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("900x600")
    app = GreenAmmoniaApp(root)
    root.mainloop()