import tkinter as tk
from tkinter import ttk

from ui.tabs import (
    RequestResponseTab, PubSubTab, MessagePassingTab, RPCTab,
    BG, BG2, BG3, ACCENT, TEXT, TEXT2, TEXT3,
    GREEN, GREEN_BG, RED, YELLOW, ORANGE, PURPLE,
)


def build_comparison_tab(notebook, tabs):
    import time

    frame = tk.Frame(notebook, bg=BG)
    notebook.add(frame, text="  Perbandingan  ")

    tk.Label(frame, text="Perbandingan Metrik Antar Model Komunikasi",
             bg=BG, fg=ACCENT, font=("Consolas", 12, "bold")).pack(pady=(12,4))
    tk.Label(frame,
             text="Jalankan simulasi di tiap tab terlebih dahulu, lalu klik Refresh.",
             bg=BG, fg=TEXT2, font=("Consolas", 9)).pack(pady=(0,8))

    #  Tabel 
    tf = tk.Frame(frame, bg=BG3); tf.pack(fill="x", padx=16, pady=4)

    HEADERS    = ["Model","Total Msg","Sukses","Gagal/Timeout",
                  "Avg Latency/RTT","Coupling","Sinkron?"]
    COL_WIDTHS = [18, 11, 9, 14, 16, 10, 9]
    ROW_FG     = [ACCENT, GREEN, ORANGE, PURPLE]
    MODEL_NAMES= ["Request-Response","Publish-Subscribe","Message Passing","RPC"]

    for i, h in enumerate(HEADERS):
        tk.Label(tf, text=h, bg=ACCENT, fg=BG2,
                 font=("Consolas", 9, "bold"), width=COL_WIDTHS[i],
                 anchor="center", padx=4, pady=6
                 ).grid(row=0, column=i, padx=1, pady=1)

    row_labels = []
    for r, name in enumerate(MODEL_NAMES):
        row = []
        bg_row = BG2 if r % 2 == 0 else BG3
        for c in range(len(HEADERS)):
            lbl = tk.Label(tf, text="-", bg=bg_row, fg=ROW_FG[r],
                           font=("Consolas", 9), width=COL_WIDTHS[c],
                           anchor="center", padx=4, pady=5)
            lbl.grid(row=r+1, column=c, padx=1, pady=1)
            row.append(lbl)
        row_labels.append(row)

    # Bar chart 
    tk.Label(frame, text="Perbandingan Total Pesan:", bg=BG, fg=TEXT2,
             font=("Consolas", 9)).pack(anchor="w", padx=16, pady=(10,0))

    bar_frame = tk.Frame(frame, bg=BG); bar_frame.pack(fill="x", padx=16, pady=2)
    bar_canvas = tk.Canvas(bar_frame, height=110, bg=BG2,
                           highlightthickness=1, highlightbackground=BG3)
    bar_canvas.pack(fill="x")

    insight_lbl = tk.Label(frame, text="", bg=BG, fg=TEXT2,
                           font=("Consolas", 9), wraplength=750, justify="left")
    insight_lbl.pack(padx=16, pady=4, anchor="w")

    def refresh():
        rr  = tabs["rr"].sim.get_metrics()
        ps  = tabs["ps"].sim.get_metrics()
        mp  = tabs["mp"].sim.get_metrics()
        rpc = tabs["rpc"].sim.get_metrics()

        data = [
            [MODEL_NAMES[0], rr["total_requests"],  rr["success"],
             rr["errors"],          f"{rr['avg_latency_ms']} ms",  "Ketat",   "Ya"],
            [MODEL_NAMES[1], ps["total_published"], ps["total_delivered"],
             0,                     "~50ms (broker)",               "Longgar", "Tidak"],
            [MODEL_NAMES[2], mp["total_sent"],      mp["total_processed"],
             mp["queue_depth"],     "Variabel (queue)",             "Longgar", "Tidak"],
            [MODEL_NAMES[3], rpc["total_calls"],    rpc["success"],
             rpc["timeouts"],       f"{rpc['avg_rtt_ms']} ms",     "Ketat",   "Ya"],
        ]

        for r, row_data in enumerate(data):
            for c, val in enumerate(row_data):
                row_labels[r][c].config(text=str(val))

        # Bar chart — responsive terhadap lebar frame
        bar_canvas.delete("all")
        totals = [int(d[1]) for d in data]
        max_v  = max(totals) if any(totals) else 1
        bar_canvas.update_idletasks()
        W = bar_canvas.winfo_width() or 700
        n = len(totals)
        margin = 24
        gap    = 12
        bar_w  = (W - 2*margin - gap*(n-1)) // n
        for i, (total, color) in enumerate(zip(totals, ROW_FG)):
            h_bar = max(4, int((total / max_v) * 75))
            x0 = margin + i * (bar_w + gap)
            x1 = x0 + bar_w
            bar_canvas.create_rectangle(x0, 100-h_bar, x1, 100,
                                        fill=color, outline="")
            bar_canvas.create_text(x0+bar_w//2, 100-h_bar-10,
                                   text=str(total), fill=color,
                                   font=("Consolas", 9, "bold"))
            bar_canvas.create_text(x0+bar_w//2, 108,
                                   text=MODEL_NAMES[i][:14], fill=TEXT3,
                                   font=("Consolas", 8))

        best = MODEL_NAMES[totals.index(max(totals))] if any(totals) else "-"
        insight_lbl.config(
            text=(f"Insight: Model dengan pesan terbanyak: {best}. "
                  f"Pub-Sub & Message Passing cocok untuk sistem skala besar (loosely coupled). "
                  f"Request-Response & RPC memberikan kepastian response langsung (tightly coupled). "
                  f"Queue depth Message Passing saat ini: {mp['queue_depth']} "
                  f"(semakin kecil = consumer tidak kewalahan)."))

    tk.Button(frame, text="↺  Refresh Data", command=refresh,
              bg=ACCENT, fg=BG2, activebackground="#1E429F", activeforeground=BG2,
              font=("Consolas", 10, "bold"), relief="flat",
              padx=20, pady=6, cursor="hand2").pack(pady=8)


def main():
    root = tk.Tk()
    root.title("Simulasi Model Komunikasi — Sistem Terdistribusi")
    root.geometry("860x700")
    root.minsize(700, 580)          # ukuran minimum supaya tidak terlalu kecil
    root.configure(bg=BG)
    root.resizable(True, True)      # bisa di-resize ke semua arah

    # Header 
    header = tk.Frame(root, bg=ACCENT, pady=8)
    header.pack(fill="x")
    tk.Label(header,
             text="Simulasi Interaktif Model Komunikasi Sistem Terdistribusi",
             bg=ACCENT, fg=BG2, font=("Consolas", 11, "bold")).pack()
    tk.Label(header,
             text="Request-Response  |  Publish-Subscribe  |  Message Passing  |  RPC",
             bg=ACCENT, fg="#BFDBFE", font=("Consolas", 8)).pack()

    # Style 
    style = ttk.Style()
    style.theme_use("default")
    style.configure("TNotebook",     background=BG,  borderwidth=0)
    style.configure("TNotebook.Tab", background=BG3, foreground=TEXT2,
                    padding=[12, 6], font=("Consolas", 9))
    style.map("TNotebook.Tab",
              background=[("selected", ACCENT)],
              foreground=[("selected", BG2)])
    style.configure("TCombobox",
                    fieldbackground=BG2, background=BG2,
                    foreground=TEXT, selectbackground=ACCENT,
                    selectforeground=BG2)

    # Notebook 
    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=6, pady=6)

    rr_tab  = RequestResponseTab(nb)
    ps_tab  = PubSubTab(nb)
    mp_tab  = MessagePassingTab(nb)
    rpc_tab = RPCTab(nb)

    tabs = {"rr": rr_tab, "ps": ps_tab, "mp": mp_tab, "rpc": rpc_tab}
    build_comparison_tab(nb, tabs)

    # Cleanup 
    def on_close():
        mp_tab.sim.stop_all()
        for tab in [rr_tab, ps_tab, mp_tab, rpc_tab]:
            tab.anim.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()