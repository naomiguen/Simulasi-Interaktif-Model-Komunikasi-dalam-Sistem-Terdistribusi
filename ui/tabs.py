import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import random

from components import SystemTopology, Packet, NodeType, NodeStatus, SystemNode
from models.request_response import RequestResponseSimulation
from models.pub_sub import PubSubSimulation
from models.message_passing import MessagePassingSimulation
from models.rpc import RPCSimulation


# Palet warna 
BG        = "#F0F2F5"   # Abu abu muda — background utama
BG2       = "#FFFFFF"   # Putih — panel/card
BG3       = "#E2E6EA"   # Abu abu sedikit lebih gelap — border/divider
ACCENT    = "#1A56DB"   # Biru tua — tombol utama
GREEN     = "#057A55"   # Hijau tua — sukses
GREEN_BG  = "#DEF7EC"   # Hijau muda — background badge sukses
RED       = "#C81E1E"   # Merah tua — error
RED_BG    = "#FDE8E8"
YELLOW    = "#92400E"   # Amber tua — warning (terbaca di putih)
PURPLE    = "#5521B5"   # Ungu tua
ORANGE    = "#B45309"   # Oranye tua
TEXT      = "#111827"   # Hitam — teks utama
TEXT2     = "#374151"   # Abu gelap — teks sekunder
TEXT3     = "#6B7280"   # Abu sedang — caption
CANVAS_BG = "#1F2937"   # Gelap — canvas animasi

NODE_COLORS = {
    NodeType.CLIENT:   ("#60A5FA", "#1E3A5F"),
    NodeType.SERVER:   ("#34D399", "#064E3B"),
    NodeType.BROKER:   ("#FBBF24", "#78350F"),
    NodeType.DATABASE: ("#A78BFA", "#2E1065"),
    NodeType.QUEUE:    ("#FCA5A5", "#7F1D1D"),
    NodeType.DEVICE:   ("#F9A8D4", "#500724"),
    NodeType.BALANCER: ("#67E8F9", "#164E63"),
}

PKT_COLORS = {
    "rr":     "#60A5FA",
    "ps":     "#34D399",
    "mp":     "#FBBF24",
    "rpc":    "#A78BFA",
    "ret_ok": "#34D399",
    "ret_err":"#F87171",
}

NODE_PKT_COLS = ["#60A5FA", "#34D399", "#FBBF24", "#A78BFA"]


def _ts():
    return time.strftime("%H:%M:%S")

class AnimatedCanvas:
    def __init__(self, parent, layout_builder):
        self.parent = parent
        self.layout_builder = layout_builder
        self.canvas = tk.Canvas(parent, bg=CANVAS_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.topology = None
        self.packets = []
        self._lock = threading.Lock()
        self._running = True
        self._last_w = 0
        self._last_h = 0
        self.canvas.bind("<Configure>", self._on_resize)
        self._animate()

    def _on_resize(self, event):
        w, h = event.width, event.height
        if w > 50 and h > 50 and (w != self._last_w or h != self._last_h):
            self._last_w, self._last_h = w, h
            self.topology = self.layout_builder(w, h)

    def add_packet(self, packet):
        with self._lock:
            self.packets.append(packet)

    def _animate(self):
        if not self._running:
            return
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w > 50 and h > 50 and (w != self._last_w or h != self._last_h):
            self._last_w, self._last_h = w, h
            self.topology = self.layout_builder(w, h)

        self.canvas.delete("all")
        self._draw_grid(w, h)
        if self.topology:
            self._draw_links()
            self._draw_nodes()
        with self._lock:
            for p in self.packets:
                p.update_position()
            self._draw_packets()
            self.packets = [p for p in self.packets if not p.is_done]
        self.canvas.after(30, self._animate)

    def _draw_grid(self, w, h):
        for x in range(0, w, 40):
            for y in range(0, h, 40):
                self.canvas.create_oval(x-1, y-1, x+1, y+1,
                                        fill="#2D3748", outline="")

    def _draw_links(self):
        for link in self.topology.links:
            self.canvas.create_line(
                link.src.canvas_x, link.src.canvas_y,
                link.dst.canvas_x, link.dst.canvas_y,
                fill="#4B5563", width=1, dash=(5, 4))

    def _draw_nodes(self):
        for node in self.topology.all_nodes():
            fg, bg = NODE_COLORS.get(node.node_type, ("#9CA3AF", "#1F2937"))
            x, y, r = node.canvas_x, node.canvas_y, 30
            self.canvas.create_oval(x-r-5, y-r-5, x+r+5, y+r+5,
                                    fill="", outline=fg, width=1)
            self.canvas.create_oval(x-r, y-r, x+r, y+r,
                                    fill=bg, outline=fg, width=2)
            self.canvas.create_text(x, y-7, text=node.name,
                                    fill=fg, font=("Consolas", 8, "bold"))
            self.canvas.create_text(x, y+8, text=node.node_type.value,
                                    fill="#9CA3AF", font=("Consolas", 7))
            dot = {"online":"#34D399","offline":"#F87171",
                   "busy":"#FBBF24","error":"#F87171"}.get(node.status.value,"#9CA3AF")
            self.canvas.create_oval(x+r-8, y-r-2, x+r+2, y-r+8,
                                    fill=dot, outline="")

    def _draw_packets(self):
        for p in self.packets:
            x, y, r = p.current_x, p.current_y, p.size
            self.canvas.create_oval(x-r+2, y-r+2, x+r+2, y+r+2,
                                    fill="#000000", outline="")
            self.canvas.create_oval(x-r, y-r, x+r, y+r,
                                    fill=p.color, outline="#FFFFFF", width=1)
            self.canvas.create_text(x, y-r-7, text=p.packet_id[:5],
                                    fill=p.color, font=("Consolas", 7))

    def stop(self):
        self._running = False


#  Komponen UI 

class LogPanel:
    def __init__(self, parent):
        self.text = scrolledtext.ScrolledText(
            parent, height=7, bg="#111827", fg="#F9FAFB",
            font=("Consolas", 9), insertbackground="#F9FAFB",
            state="disabled", relief="flat", selectbackground=ACCENT)
        self.text.pack(fill="both", expand=True, padx=6, pady=4)
        self.text.tag_config("ok",   foreground="#34D399")
        self.text.tag_config("err",  foreground="#F87171")
        self.text.tag_config("info", foreground="#93C5FD")
        self.text.tag_config("warn", foreground="#FCD34D")

    def append(self, msg):
        tag = ("ok"   if any(c in msg for c in ["✓","Sukses","sukses"]) else
               "err"  if any(c in msg for c in ["✗","ERROR","TIMEOUT"]) else
               "warn" if "⚠" in msg else "info")
        self.text.configure(state="normal")
        self.text.insert("end", msg + "\n", tag)
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")


class MetricCard:
    def __init__(self, parent, label, color=ACCENT):
        frame = tk.Frame(parent, bg=BG2, highlightthickness=1,
                         highlightbackground=BG3)
        frame.pack(side="left", padx=4, pady=4, ipadx=12, ipady=6)
        tk.Label(frame, text=label, bg=BG2, fg=TEXT3,
                 font=("Consolas", 8)).pack()
        self.val = tk.Label(frame, text="0", bg=BG2, fg=color,
                            font=("Consolas", 15, "bold"))
        self.val.pack()

    def set(self, value):
        self.val.config(text=str(value))


def _desc(parent, text):
    tk.Label(parent, text=text, bg=BG3, fg=TEXT2, font=("Consolas", 9),
             wraplength=700, justify="left", padx=10, pady=6
             ).pack(fill="x", padx=10, pady=(4, 2))


def _section(parent, text):
    tk.Label(parent, text=text, bg=BG, fg=TEXT2,
             font=("Consolas", 9, "bold")).pack(anchor="w", padx=10, pady=(6,1))


def _btn(parent, text, cmd, primary=False, color=None):
    bg = color or (ACCENT if primary else BG3)
    fg = BG2 if primary else TEXT2
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                     activebackground="#1E429F", activeforeground=BG2,
                     font=("Consolas", 9, "bold" if primary else "normal"),
                     relief="flat", padx=10, pady=4, cursor="hand2")


def _entry(parent, var, width=16):
    return tk.Entry(parent, textvariable=var, width=width,
                    bg=BG2, fg=TEXT, insertbackground=TEXT,
                    font=("Consolas", 9), relief="solid",
                    highlightthickness=1, highlightbackground=BG3)


def _lbl(parent, text):
    tk.Label(parent, text=text, bg=BG, fg=TEXT2,
             font=("Consolas", 9)).pack(side="left", padx=(6,0))


def _slider(parent, var, from_, to, lbl_widget):
    tk.Scale(parent, from_=from_, to=to, variable=var,
             orient="horizontal", length=110, bg=BG, fg=TEXT,
             troughcolor=BG3, highlightthickness=0, showvalue=False,
             command=lambda v: lbl_widget.config(
                 text=f"{int(float(v))} ms")).pack(side="left")

# TAB 1 — REQUEST-RESPONSE

class RequestResponseTab:
    def __init__(self, nb):
        self.sim = RequestResponseSimulation()
        self.frame = tk.Frame(nb, bg=BG)
        nb.add(self.frame, text="  Request-Response  ")
        self._build()

    def _build(self):
        _desc(self.frame,
              "Model Sinkron: Client mengirim request dan MENUNGGU response dari server. "
              "Jika server error, client langsung mendapat respons gagal.")
        self.anim = AnimatedCanvas(self.frame,
                                   lambda w,h: SystemTopology.build_request_response(w,h))
        mf = tk.Frame(self.frame, bg=BG); mf.pack(fill="x", padx=10)
        self.m_total   = MetricCard(mf, "Total Request", ACCENT)
        self.m_ok      = MetricCard(mf, "Sukses", GREEN)
        self.m_err     = MetricCard(mf, "Error", RED)
        self.m_latency = MetricCard(mf, "Avg Latency (ms)", YELLOW)

        cf = tk.Frame(self.frame, bg=BG); cf.pack(fill="x", padx=10, pady=4)
        _lbl(cf, "Payload:")
        self.payload_var = tk.StringVar(value="GET /user/data")
        _entry(cf, self.payload_var, 18).pack(side="left", padx=4)

        _lbl(cf, "Latency:")
        self.lat_var = tk.IntVar(value=600)
        self.lat_lbl = tk.Label(cf, text="600 ms", bg=BG, fg=ACCENT,
                                font=("Consolas", 9, "bold"), width=7)
        self.lat_lbl.pack(side="left", padx=2)
        _slider(cf, self.lat_var, 100, 2000, self.lat_lbl)

        _btn(cf, " Kirim Request", self._send, primary=True).pack(side="left", padx=8)
        _btn(cf, "Reset", self._reset).pack(side="left")

        _section(self.frame, "Log Komunikasi")
        self.log = LogPanel(self.frame)

    def _topo(self): return self.anim.topology

    def _send(self):
        payload = self.payload_var.get() or "GET /data"
        lat = self.lat_var.get()
        topo = self._topo()
        if topo:
            c, s = topo.get_node("rr_client"), topo.get_node("rr_server")
            if c and s:
                self.anim.add_packet(
                    Packet(f"REQ-{self.sim.client.request_count+1:04d}",
                           c, s, payload, color=PKT_COLORS["rr"], size=9))
        self.log.append(f"[{_ts()}] → Request: '{payload}' | latency={lat}ms")

        def on_done(resp):
            topo2 = self._topo()
            if topo2:
                c2, s2 = topo2.get_node("rr_client"), topo2.get_node("rr_server")
                if c2 and s2:
                    col = PKT_COLORS["ret_ok"] if resp.status=="OK" else PKT_COLORS["ret_err"]
                    self.anim.add_packet(
                        Packet(resp.request_id, s2, c2, resp.data,
                               color=col, size=9, is_return=True))
            icon = "✓" if resp.status=="OK" else "✗"
            self.log.append(f"[{_ts()}] {icon} {resp.request_id}: {resp.data} ({lat}ms)")
            self._refresh()

        self.sim.run_once(payload, lat, callback=on_done)

    def _refresh(self):
        m = self.sim.get_metrics()
        self.m_total.set(m["total_requests"]); self.m_ok.set(m["success"])
        self.m_err.set(m["errors"]); self.m_latency.set(m["avg_latency_ms"])

    def _reset(self):
        self.sim.reset(); self.log.clear(); self._refresh()
        self.log.append(f"[{_ts()}] Simulasi di-reset.")


# TAB 2 — PUBLISH-SUBSCRIBE
class PubSubTab:
    def __init__(self, nb):
        self.sim = PubSubSimulation()
        self._t0 = time.time()
        self.frame = tk.Frame(nb, bg=BG)
        nb.add(self.frame, text="  Publish-Subscribe  ")
        self._build()

    def _build(self):
        _desc(self.frame,
              "Model Asinkron: Publisher → Broker → semua Subscriber terdaftar. "
              "Publisher tidak perlu tahu siapa penerimanya (loosely coupled).")
        self.anim = AnimatedCanvas(self.frame,
                                   lambda w,h: SystemTopology.build_pub_sub(w,h))
        mf = tk.Frame(self.frame, bg=BG); mf.pack(fill="x", padx=10)
        self.m_pub  = MetricCard(mf, "Diterbitkan", ACCENT)
        self.m_del  = MetricCard(mf, "Terkirim ke Sub", GREEN)
        self.m_subs = MetricCard(mf, "Subscriber Aktif", ORANGE)
        self.m_tp   = MetricCard(mf, "Throughput /s", YELLOW)

        cf = tk.Frame(self.frame, bg=BG); cf.pack(fill="x", padx=10, pady=4)
        _lbl(cf, "Publisher:")
        self.pub_var = tk.StringVar(value="Publisher-1")
        ttk.Combobox(cf, textvariable=self.pub_var, width=13,
                     values=["Publisher-1","Publisher-2"],
                     state="readonly").pack(side="left", padx=4)
        _lbl(cf, "Topic:")
        self.topic_var = tk.StringVar(value="orders")
        ttk.Combobox(cf, textvariable=self.topic_var, width=11,
                     values=["orders","payments","alerts"],
                     state="readonly").pack(side="left", padx=4)
        _lbl(cf, "Pesan:")
        self.msg_var = tk.StringVar(value="Event baru")
        _entry(cf, self.msg_var, 14).pack(side="left", padx=4)
        _btn(cf, "Publish", self._publish, primary=True).pack(side="left", padx=6)
        _btn(cf, "+ Subscriber", self._add_sub, color=GREEN_BG).pack(side="left", padx=2)
        _btn(cf, "Reset", self._reset).pack(side="left", padx=4)

        _section(self.frame, "Log Komunikasi")
        self.log = LogPanel(self.frame)

    def _topo(self): return self.anim.topology

    def _publish(self):
        pub_idx = 0 if "1" in self.pub_var.get() else 1
        topic   = self.topic_var.get()
        content = self.msg_var.get() or "event"
        color   = {"orders":PKT_COLORS["rr"],"payments":PKT_COLORS["ps"],
                   "alerts":PKT_COLORS["ret_err"]}.get(topic, PKT_COLORS["mp"])

        topo = self._topo()
        if topo:
            pn = topo.get_node(f"ps_pub{pub_idx+1}")
            bn = topo.get_node("ps_broker")
            if pn and bn:
                self.anim.add_packet(Packet("PUB", pn, bn, content, color=color, size=9))

        self.log.append(f"[{_ts()}] 📢 [{self.pub_var.get()}] → topic '{topic}': '{content}'")
        n_subs = len(self.sim.subscribers)

        def on_done():
            topo2 = self._topo()
            if not topo2: return
            bn2 = topo2.get_node("ps_broker")
            for i in range(n_subs):
                sn = topo2.get_node(f"ps_sub{i+1}")
                if bn2 and sn:
                    def _send(s=sn, d=i*0.12):
                        time.sleep(d)
                        self.anim.add_packet(Packet("MSG", bn2, s, content, color=color, size=7))
                        self.log.append(f"[{_ts()}] ✓ {s.name} menerima topic '{topic}'")
                        self._refresh()
                    threading.Thread(target=_send, daemon=True).start()

        self.sim.publish(pub_idx, topic, content, callback=on_done)
        self._refresh()

    def _add_sub(self):
        n = len(self.sim.subscribers) + 1
        if n > 6:
            self.log.append(f"[{_ts()}] Maksimum 6 subscriber"); return
        name = f"Subscriber-{n}"
        self.sim.add_subscriber(name, ["orders"])
        topo = self._topo()
        if topo:
            bn = topo.get_node("ps_broker")
            if bn:
                w = self.anim.canvas.winfo_width()
                new = SystemNode(f"ps_sub{n}", name, NodeType.CLIENT,
                                 canvas_x=bn.canvas_x + int(w*0.28),
                                 canvas_y=40 + n*40)
                topo.add_node(new)
                topo.add_link("ps_broker", f"ps_sub{n}")
        self.log.append(f"[{_ts()}] + {name} bergabung ke topic 'orders'")
        self._refresh()

    def _refresh(self):
        m = self.sim.get_metrics()
        self.m_pub.set(m["total_published"]); self.m_del.set(m["total_delivered"])
        self.m_subs.set(m["active_subscribers"])
        elapsed = max(1, time.time()-self._t0)
        self.m_tp.set(f"{m['total_published']/elapsed:.1f}")

    def _reset(self):
        self.sim.reset(); self._t0 = time.time(); self.log.clear()
        w = self.anim.canvas.winfo_width(); h = self.anim.canvas.winfo_height()
        self.anim.topology = SystemTopology.build_pub_sub(w, h)
        self._refresh(); self.log.append(f"[{_ts()}] Simulasi di-reset.")


# TAB 3 — MESSAGE PASSING
class MessagePassingTab:
    def __init__(self, nb):
        self.sim = MessagePassingSimulation()
        self.frame = tk.Frame(nb, bg=BG)
        nb.add(self.frame, text="  Message Passing  ")
        self._build()
        self.sim.start_all(callback=self._on_processed)

    _IDS = ["mp_a","mp_b","mp_c","mp_d"]
    _MAP = {"Node-A":0,"Node-B":1,"Node-C":2,"Node-D":3}

    def _build(self):
        _desc(self.frame,
              "Model Asinkron via Queue: Pengirim menaruh pesan di queue, "
              "node penerima ambil dan proses saat siap — tidak harus online bersamaan.")
        self.anim = AnimatedCanvas(self.frame,
                                   lambda w,h: SystemTopology.build_message_passing(w,h))
        mf = tk.Frame(self.frame, bg=BG); mf.pack(fill="x", padx=10)
        self.m_queue = MetricCard(mf, "Di Queue", YELLOW)
        self.m_proc  = MetricCard(mf, "Diproses", GREEN)
        self.m_sent  = MetricCard(mf, "Dikirim", ACCENT)
        self.m_wait  = MetricCard(mf, "Avg Wait (ms)", ORANGE)

        cf = tk.Frame(self.frame, bg=BG); cf.pack(fill="x", padx=10, pady=4)
        NAMES = ["Node-A","Node-B","Node-C","Node-D"]
        _lbl(cf, "Dari:")
        self.from_var = tk.StringVar(value="Node-A")
        ttk.Combobox(cf, textvariable=self.from_var, width=9,
                     values=NAMES, state="readonly").pack(side="left", padx=4)
        _lbl(cf, "Ke:")
        self.to_var = tk.StringVar(value="Node-B")
        ttk.Combobox(cf, textvariable=self.to_var, width=9,
                     values=NAMES, state="readonly").pack(side="left", padx=4)
        _lbl(cf, "Priority:")
        self.prio_var = tk.IntVar(value=1)
        ttk.Combobox(cf, textvariable=self.prio_var, width=4,
                     values=[1,2,3], state="readonly").pack(side="left", padx=4)
        _lbl(cf, "Isi:")
        self.content_var = tk.StringVar(value="Data task")
        _entry(cf, self.content_var, 13).pack(side="left", padx=4)
        _btn(cf, "Kirim", self._send, primary=True).pack(side="left", padx=6)
        _btn(cf, "Reset", self._reset).pack(side="left")

        _section(self.frame, "Log Komunikasi")
        self.log = LogPanel(self.frame)

    def _topo(self): return self.anim.topology

    def _send(self):
        fi = self._MAP.get(self.from_var.get(), 0)
        ti = self._MAP.get(self.to_var.get(), 1)
        if fi == ti:
            self.log.append(f"[{_ts()}] ⚠ Pilih node tujuan berbeda!"); return
        prio = self.prio_var.get(); content = self.content_var.get() or "data"
        topo = self._topo()
        if topo:
            fn = topo.get_node(self._IDS[fi]); qn = topo.get_node("mp_q")
            if fn and qn:
                self.anim.add_packet(Packet("MP", fn, qn, content,
                                            color=NODE_PKT_COLS[fi], size=9))
        ok = self.sim.send_message(fi, ti, content, prio)
        msg = (f"[{_ts()}] → {self.from_var.get()} → Queue → "
               f"{self.to_var.get()} | '{content}' | priority={prio}")
        self.log.append(msg if ok else f"[{_ts()}] ✗ Queue penuh!")
        self._refresh()

    def _on_processed(self, message, node_name):
        ti = self._MAP.get(node_name, 0); topo = self._topo()
        if topo:
            qn = topo.get_node("mp_q"); dn = topo.get_node(self._IDS[ti])
            if qn and dn:
                self.anim.add_packet(Packet("MP", qn, dn, message.content,
                                            color=NODE_PKT_COLS[ti], size=9, is_return=True))
        self.log.append(f"[{_ts()}] ✓ {node_name} selesai: '{message.content}'")
        self._refresh()

    def _refresh(self):
        m = self.sim.get_metrics()
        self.m_queue.set(m["queue_depth"]); self.m_proc.set(m["total_processed"])
        self.m_sent.set(m["total_sent"])
        waits = [(msg.process_time-msg.enqueue_time)*1000
                 for n in self.sim.nodes for msg in n.processed_messages if msg.process_time]
        self.m_wait.set(round(sum(waits)/len(waits),1) if waits else 0)

    def _reset(self):
        self.sim.reset(callback=self._on_processed); self.log.clear()
        self._refresh(); self.log.append(f"[{_ts()}] Simulasi di-reset.")


# TAB 4 — RPC
class RPCTab:
    def __init__(self, nb):
        self.sim = RPCSimulation()
        self.frame = tk.Frame(nb, bg=BG)
        nb.add(self.frame, text="  RPC  ")
        self._build()

    _ARGS = {
        "getUser":          {"user_id": 1},
        "calcPrice":        {"quantity": 3, "unit_price": 75000.0},
        "sendNotification": {"email": "user@example.com", "message": "Halo!"},
        "processOrder":     {"product_id": 42, "quantity": 2, "customer": "Andi"},
    }
    _RPC_IDS = ["rpc_client","rpc_stub","rpc_skeleton","rpc_server"]

    def _build(self):
        _desc(self.frame,
              "Remote Procedure Call: Client panggil fungsi di server seolah lokal. "
              "Proses marshal→network→unmarshal disembunyikan. Delay > 2000ms → TIMEOUT.")
        self.anim = AnimatedCanvas(self.frame,
                                   lambda w,h: SystemTopology.build_rpc(w,h))
        mf = tk.Frame(self.frame, bg=BG); mf.pack(fill="x", padx=10)
        self.m_calls   = MetricCard(mf, "Pemanggilan", ACCENT)
        self.m_ok      = MetricCard(mf, "Sukses", GREEN)
        self.m_timeout = MetricCard(mf, "Timeout", RED)
        self.m_rtt     = MetricCard(mf, "Avg RTT (ms)", PURPLE)

        cf = tk.Frame(self.frame, bg=BG); cf.pack(fill="x", padx=10, pady=4)
        _lbl(cf, "Prosedur:")
        self.proc_var = tk.StringVar(value="getUser")
        ttk.Combobox(cf, textvariable=self.proc_var, width=18,
                     values=self.sim.server.available_procedures,
                     state="readonly").pack(side="left", padx=4)
        _lbl(cf, "Network delay:")
        self.delay_var = tk.IntVar(value=400)
        self.delay_lbl = tk.Label(cf, text="400 ms", bg=BG, fg=ACCENT,
                                  font=("Consolas", 9, "bold"), width=7)
        self.delay_lbl.pack(side="left", padx=2)
        _slider(cf, self.delay_var, 100, 3000, self.delay_lbl)
        _btn(cf, "Panggil RPC", self._call, primary=True).pack(side="left", padx=8)
        _btn(cf, "Reset", self._reset).pack(side="left")

        _section(self.frame, "Log Komunikasi")
        self.log = LogPanel(self.frame)

    def _topo(self): return self.anim.topology

    def _call(self):
        proc = self.proc_var.get(); delay = self.delay_var.get()
        args = self._ARGS.get(proc, {})
        topo = self._topo()
        nodes = {nid: (topo.get_node(nid) if topo else None) for nid in self._RPC_IDS}
        self.log.append(f"[{_ts()}] → {proc}({args}) [delay={delay}ms, timeout=2000ms]")

        def _fwd():
            pairs = [("rpc_client","rpc_stub"),("rpc_stub","rpc_skeleton"),
                     ("rpc_skeleton","rpc_server")]
            for i,(s,d) in enumerate(pairs):
                time.sleep(i*0.15)
                if nodes.get(s) and nodes.get(d):
                    p = Packet("CALL", nodes[s], nodes[d], proc,
                               color=PKT_COLORS["rpc"], size=8)
                    p.speed = 0.035; self.anim.add_packet(p)
        threading.Thread(target=_fwd, daemon=True).start()

        def on_done(resp):
            col = PKT_COLORS["ret_ok"] if resp.status=="SUCCESS" else PKT_COLORS["ret_err"]
            def _ret():
                pairs = [("rpc_server","rpc_skeleton"),("rpc_skeleton","rpc_stub"),
                         ("rpc_stub","rpc_client")]
                for i,(s,d) in enumerate(pairs):
                    time.sleep(i*0.15)
                    if nodes.get(s) and nodes.get(d):
                        p = Packet("RET", nodes[s], nodes[d], str(resp.result),
                                   color=col, size=8, is_return=True)
                        p.speed = 0.035; self.anim.add_packet(p)
            threading.Thread(target=_ret, daemon=True).start()
            if resp.status=="SUCCESS":
                self.log.append(f"[{_ts()}] ✓ {proc} sukses [RTT={resp.rtt_ms:.0f}ms] → {resp.result}")
            elif resp.status=="TIMEOUT":
                self.log.append(f"[{_ts()}] ✗ TIMEOUT: {proc} melebihi 2000ms")
            else:
                self.log.append(f"[{_ts()}] ✗ ERROR: {resp.error_msg}")
            self._refresh()

        self.sim.call(proc, delay, callback=on_done, **args)

    def _refresh(self):
        m = self.sim.get_metrics()
        self.m_calls.set(m["total_calls"]); self.m_ok.set(m["success"])
        self.m_timeout.set(m["timeouts"]); self.m_rtt.set(m["avg_rtt_ms"])

    def _reset(self):
        self.sim.reset(); self.log.clear(); self._refresh()
        self.log.append(f"[{_ts()}] Simulasi di-reset.")


# ekspor warna untuk main.py
NODE_PKT_COLS = ["#60A5FA","#34D399","#FBBF24","#A78BFA"]