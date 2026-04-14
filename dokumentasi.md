# Dokumentasi Simulasi Interaktif Model Komunikasi dalam Sistem Terdistribusi

**Bahasa:** Python 3.10+  
**Library:** `tkinter`, `threading`, `queue`, `dataclasses` — semua bawaan Python, tidak perlu install tambahan  
**Cara jalankan:**
```bash
# Masuk ke folder proyek
cd "TUGAS 2 SISTER"

# Jalankan program
python main.py
```

---

## Struktur Folder

```
TUGAS 2 SISTER/
├── main.py                   # Entry point — menjalankan GUI utama
├── components.py             # Definisi komponen sistem terdistribusi
├── dokumentasi.md            # File dokumentasi proyek ini
├── models/
│   ├── message_passing.py    # Model komunikasi 3: Message Passing
│   ├── pub_sub.py            # Model komunikasi 2: Publish-Subscribe
│   ├── request_response.py   # Model komunikasi 1: Request-Response
│   └── rpc.py                # Model komunikasi 4: RPC
└── ui/
    └── tabs.py               # GUI: canvas animasi, tab, kontrol pengguna
```

---

## Cara Menjalankan Program

### Persyaratan
- Python versi 3.10 atau lebih baru
- Tidak perlu install library eksternal apapun

### Langkah-langkah
```bash
# 1. Masuk ke folder proyek
cd "TUGAS 2 SISTER"

# 2. Jalankan program
python main.py
```

### Yang muncul setelah dijalankan
- Jendela GUI berukuran 860×700 pixel terbuka
- Terdapat 5 tab: **Request-Response**, **Publish-Subscribe**, **Message Passing**, **RPC**, dan **Perbandingan**
- Window bisa di-resize ke segala ukuran. posisi node di canvas otomatis menyesuaikan

---

## File 1: `components.py`

### Fungsi File
Mendefinisikan semua **komponen dasar sistem terdistribusi** yang dipakai bersama oleh semua model komunikasi. File ini tidak berisi logika komunikasi, hanya struktur data dan representasi visual.

### Isi dan Penjelasan Kode

#### `NodeType` — Enum tipe node
```python
class NodeType(Enum):
    CLIENT   = "Client"
    SERVER   = "Server"
    BROKER   = "Broker"
    DATABASE = "Database"
    DEVICE   = "Device"
    BALANCER = "Load Balancer"
    QUEUE    = "Queue"
```
Mendefinisikan semua jenis entitas yang bisa ada dalam sistem terdistribusi. Setiap tipe ditampilkan dengan warna berbeda di canvas.

#### `NodeStatus` — Enum status node
```python
class NodeStatus(Enum):
    ONLINE  = "online"
    OFFLINE = "offline"
    BUSY    = "busy"
    ERROR   = "error"
```
Status node ditampilkan sebagai titik berwarna di pojok kanan atas node di canvas. Hijau = online, merah = error/offline, kuning = busy.

#### `SystemNode` — Komponen dasar sistem
```python
@dataclass
class SystemNode:
    node_id:    str
    name:       str
    node_type:  NodeType
    host:       str = "localhost"
    port:       int = 8080
    status:     NodeStatus = NodeStatus.ONLINE
    canvas_x:   float = 0.0
    canvas_y:   float = 0.0
    messages_sent:     int = 0
    messages_received: int = 0
    uptime_start:      float = field(default_factory=time.time)
```
Representasi satu entitas dalam sistem (client, server, broker, dll). `canvas_x` dan `canvas_y` adalah posisi node di layar GUI. Setiap node menyimpan statistik berapa banyak pesan yang dikirim dan diterima.

#### `Packet` — Unit data yang bergerak di canvas
```python
@dataclass
class Packet:
    packet_id:  str
    src_node:   SystemNode
    dst_node:   SystemNode
    content:    str
    color:      str = "#378ADD"
    size:       int = 8
    progress:   float = 0.0
    speed:      float = 0.02
    current_x:  float = 0.0
    current_y:  float = 0.0
    is_return:  bool = False

    def update_position(self):
        self.progress = min(1.0, self.progress + self.speed)
        self.current_x = self.src_node.canvas_x + (self.dst_node.canvas_x - self.src_node.canvas_x) * self.progress
        self.current_y = self.src_node.canvas_y + (self.dst_node.canvas_y - self.src_node.canvas_y) * self.progress
```
Paket data dianimasikan sebagai lingkaran kecil yang bergerak dari node sumber ke node tujuan. `progress` bertambah setiap frame dari 0.0 (di sumber) sampai 1.0 (di tujuan). Posisi dihitung dengan interpolasi linear.

#### `NetworkLink` — Koneksi antar node
```python
@dataclass
class NetworkLink:
    src:       SystemNode
    dst:       SystemNode
    bandwidth: float = 100.0
    latency:   float = 10.0
    active:    bool  = True
```
Representasi koneksi jaringan antara dua node. Ditampilkan sebagai garis putus-putus di canvas.

#### `SystemTopology` — Kumpulan node dan link
```python
class SystemTopology:
    def build_request_response(canvas_w, canvas_h) -> SystemTopology
    def build_pub_sub(canvas_w, canvas_h) -> SystemTopology
    def build_message_passing(canvas_w, canvas_h) -> SystemTopology
    def build_rpc(canvas_w, canvas_h) -> SystemTopology
```
Setiap model komunikasi punya topologi berbeda. Topologi dibangun ulang setiap kali window di-resize karena menerima `canvas_w` dan `canvas_h` sebagai parameter, sehingga posisi node selalu proporsional terhadap ukuran layar.

| Topologi | Node yang ada |
|---|---|
| Request-Response | Client, Server, Database |
| Publish-Subscribe | Publisher-1, Publisher-2, Broker, Subscriber-1,2,3 |
| Message Passing | Node-A, Node-B, Node-C, Node-D, Queue |
| RPC | Client, Stub, Skeleton, Server |

---

## File 2: `models/request_response.py`

### Fungsi File
Mengimplementasikan logika model **Request-Response** — model komunikasi sinkron paling dasar. Client mengirim request dan memblokir eksekusi (menunggu) sampai server mengirimkan response.

### Isi dan Penjelasan Kode

#### `Request` dan `Response` — Struktur data pesan
```python
@dataclass
class Request:
    request_id: str
    sender: str
    receiver: str
    payload: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class Response:
    request_id: str
    status: str      # "OK" atau "ERROR"
    data: str
    latency_ms: float
    timestamp: float = field(default_factory=time.time)
```
Setiap request punya ID unik (format `REQ-0001`) dan timestamp kapan dikirim. Response membawa status apakah berhasil atau gagal.

#### `Server` — Menerima dan memproses request
```python
class Server:
    def __init__(self, name: str, error_rate: float = 0.2):
        ...

    def handle_request(self, request: Request, latency_ms: float = 500) -> Response:
        time.sleep(latency_ms / 1000)           # Simulasi waktu proses
        if random.random() < self.error_rate:   # Simulasi kemungkinan error
            return Response(status="ERROR", ...)
        return Response(status="OK", ...)
```
`error_rate=0.2` berarti 20% dari semua request akan gagal secara acak. `time.sleep(latency_ms/1000)` mensimulasikan beban kerja server.

#### `Client` — Mengirim request secara sinkron
```python
class Client:
    def send_request(self, server: Server, payload: str, latency_ms: float) -> Response:
        response = server.handle_request(request, latency_ms)   # BLOCKING
        ...
        return response
```
Baris `server.handle_request(...)` adalah operasi **blocking** — client berhenti di sini dan tidak melanjutkan apapun sampai server selesai memproses.

#### `RequestResponseSimulation` — Kelas penghubung ke GUI
```python
class RequestResponseSimulation:
    def run_once(self, payload, latency_ms, callback=None):
        def _run():
            response = self.client.send_request(self.server, payload, latency_ms)
            if callback:
                callback(response)
        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def get_metrics(self) -> dict:
        return {
            "total_requests": ...,
            "success": ...,
            "errors": ...,
            "avg_latency_ms": ...,
        }
```
`run_once()` menjalankan satu siklus di **thread terpisah** agar jendela GUI tidak freeze. Logika di dalamnya tetap sinkron (client menunggu server). `get_metrics()` dipakai oleh GUI untuk memperbarui kartu statistik.

---

## File 3: `models/pub_sub.py`

### Fungsi File
Mengimplementasikan model **Publish-Subscribe** — model asinkron berbasis event. Publisher tidak mengetahui siapa penerimanya. Broker bertugas mendistribusikan pesan ke semua subscriber yang terdaftar pada topic tertentu.

### Isi dan Penjelasan Kode

#### `Message` — Struktur pesan Pub-Sub
```python
@dataclass
class Message:
    msg_id: str
    topic: str
    publisher: str
    content: str
    timestamp: float = field(default_factory=time.time)
```
Pesan memiliki `topic` — ini yang membedakan Pub-Sub dari model lain. Publisher tidak menyebut nama subscriber, hanya nama topic.

#### `Broker` — Jantung sistem Pub-Sub
```python
class Broker:
    def subscribe(self, topic: str, subscriber_name: str, callback: Callable):
        self._subscriptions[topic].append((subscriber_name, callback))

    def publish(self, message: Message):
        subscribers = self._subscriptions.get(message.topic, [])
        for sub_name, callback in subscribers:
            t = threading.Thread(target=self._deliver, args=(message, sub_name, callback))
            t.start()

    def _deliver(self, message, sub_name, callback):
        time.sleep(0.05)
        callback(message)
```
`_subscriptions` adalah dictionary `{topic: [(nama_sub, callback), ...]}`. Saat ada pesan masuk ke suatu topic, broker membuat **thread terpisah untuk setiap subscriber** — pengiriman ke semua subscriber terjadi secara paralel dan asinkron. Publisher sudah selesai dan bisa lanjut ke tugas lain sebelum semua subscriber menerima pesan.

#### `Publisher` — Mengirim ke topic tanpa tahu siapa penerima
```python
class Publisher:
    def publish(self, topic: str, content: str):
        self.broker.publish(msg)    # Asinkron — publisher tidak menunggu
```

#### `Subscriber` — Mendaftar ke topic, menerima via callback
```python
class Subscriber:
    def subscribe(self, topic: str):
        self.broker.subscribe(topic, self.name, self._on_message)

    def _on_message(self, message: Message):
        self.received_messages.append(message)
```
Subscriber mendaftarkan fungsi `_on_message` sebagai callback. Broker akan memanggil callback ini setiap ada pesan baru di topic yang disubscribe.

#### Setup awal subscriber dan topic
```python
# Subscriber-1 subscribe ke: orders, payments
# Subscriber-2 subscribe ke: orders, alerts
# Subscriber-3 subscribe ke: payments, alerts
```
Artinya jika Publisher publish ke topic `orders`, maka Subscriber-1 dan Subscriber-2 yang menerima. Subscriber-3 tidak menerima karena tidak subscribe ke `orders`.

---

## File 4: `models/message_passing.py`

### Fungsi File
Mengimplementasikan model **Message Passing** berbasis queue. Pengirim menaruh pesan di antrian (queue) milik node tujuan, lalu node tujuan mengambil dan memproses pesan saat siap. Pengirim dan penerima tidak harus aktif bersamaan.

### Isi dan Penjelasan Kode

#### `QueueMessage` — Struktur pesan dengan prioritas
```python
@dataclass
class QueueMessage:
    msg_id: str
    sender: str
    receiver: str
    content: str
    priority: int = 1       # 1=normal, 2=high, 3=urgent
    enqueue_time: float = field(default_factory=time.time)
    process_time: Optional[float] = None
```
`enqueue_time` dicatat saat pesan masuk queue. `process_time` dicatat saat pesan mulai diproses. Selisih keduanya adalah **queue wait time** yang ditampilkan di metrik.

#### `MessageQueue` — Antrian dengan prioritas
```python
class MessageQueue:
    def __init__(self, name: str, maxsize: int = 20):
        self._queue = queue.PriorityQueue(maxsize=maxsize)

    def put(self, message: QueueMessage) -> bool:
        priority_key = (4 - message.priority, message.enqueue_time)
        self._queue.put_nowait((priority_key, message))

    def get(self, timeout: float = 1.0) -> Optional[QueueMessage]:
        _, message = self._queue.get(timeout=timeout)
        return message
```
Menggunakan `queue.PriorityQueue` bawaan Python. Prioritas dibalik (`4 - priority`) karena PriorityQueue Python mengambil nilai **terkecil** duluan, sedangkan kita ingin angka **terbesar** (3=urgent) yang diambil duluan. Queue memiliki batas maksimum 20 pesan — jika penuh, `put()` mengembalikan `False`.

#### `Node` — Entitas yang bisa kirim dan terima pesan
```python
class Node:
    def __init__(self, name: str, process_time_ms: float = 300):
        self.inbox = MessageQueue(f"{name}-inbox")

    def send(self, message: QueueMessage, target_node: 'Node') -> bool:
        return target_node.inbox.put(message)

    def start_processing(self, callback=None):
        self._running = True
        def _worker():
            while self._running:
                msg = self.inbox.get(timeout=0.5)
                if msg:
                    self._process_message(msg, callback)
        threading.Thread(target=_worker, daemon=True).start()
```
Setiap node punya **inbox queue** sendiri. `start_processing()` menjalankan worker thread yang terus-menerus mengambil pesan dari inbox dan memprosesnya. Worker thread ini jalan di background secara independen.

Kecepatan proses setiap node berbeda-beda:
- Node-A: 200ms per pesan
- Node-B: 400ms per pesan
- Node-C: 150ms per pesan (tercepat)
- Node-D: 500ms per pesan (terlambat)

---

## File 5: `models/rpc.py`

### Fungsi File
Mengimplementasikan model **Remote Procedure Call (RPC)**. Client memanggil prosedur di server seolah-olah memanggil fungsi lokal. Di balik layar terjadi proses marshalling argumen, transmisi jaringan, eksekusi di server, lalu hasilnya dikembalikan ke client. Terdapat mekanisme **timeout** — jika server terlalu lama merespons, client mendapat status TIMEOUT.

### Isi dan Penjelasan Kode

#### `RPCRequest` dan `RPCResponse` — Struktur data RPC
```python
@dataclass
class RPCRequest:
    call_id: str
    procedure: str
    args: dict
    caller: str

@dataclass
class RPCResponse:
    call_id: str
    procedure: str
    result: Any
    status: str         # "SUCCESS", "TIMEOUT", "ERROR"
    error_msg: str = ""
    execution_time_ms: float = 0.0
    rtt_ms: float = 0.0
```
`rtt_ms` adalah Round-Trip Time — total waktu dari client kirim hingga client terima response, termasuk network delay dua arah.

#### `RPCServer` — Mendaftarkan dan mengeksekusi prosedur
```python
class RPCServer:
    def _register_default_procedures(self):
        def get_user(user_id: int) -> dict: ...
        def calc_price(quantity: int, unit_price: float) -> dict: ...
        def send_notification(email: str, message: str) -> dict: ...
        def process_order(product_id: int, quantity: int, customer: str) -> dict: ...

        self._procedures = {
            "getUser": get_user,
            "calcPrice": calc_price,
            "sendNotification": send_notification,
            "processOrder": process_order,
        }

    def execute(self, request: RPCRequest, network_delay_ms: float) -> RPCResponse:
        time.sleep(network_delay_ms / 2 / 1000)   # Simulasi delay jaringan (pergi)
        result = self._procedures[request.procedure](**request.args)
        time.sleep(network_delay_ms / 2 / 1000)   # Simulasi delay jaringan (balik)
        return RPCResponse(status="SUCCESS", result=result, ...)
```
Network delay dibagi dua — setengah untuk perjalanan request dari client ke server, setengah lagi untuk perjalanan response dari server ke client.

#### `RPCClient` — Memanggil prosedur remote dengan timeout
```python
class RPCClient:
    def call(self, procedure: str, network_delay_ms: float, **kwargs) -> RPCResponse:
        result_holder = []
        def _do_call():
            resp = self.server.execute(request, network_delay_ms)
            result_holder.append(resp)

        worker = threading.Thread(target=_do_call, daemon=True)
        worker.start()
        worker.join(timeout=self.timeout_ms / 1000)   # Tunggu maksimal 2000ms

        if not result_holder:
            return RPCResponse(status="TIMEOUT", ...)   # Server terlalu lama
        return result_holder[0]
```
Mekanisme timeout menggunakan `thread.join(timeout=...)`. Jika thread selesai sebelum timeout, `result_holder` berisi response. Jika tidak (timeout), `result_holder` kosong dan client mengembalikan status TIMEOUT. Ini mensimulasikan kondisi network partition atau server overload.

---

## File 6: `ui/tabs.py`

### Fungsi File
Berisi seluruh **komponen GUI** — canvas animasi, kartu metrik, log komunikasi, dan kontrol pengguna (tombol, slider, dropdown) untuk setiap tab model komunikasi.

### Isi dan Penjelasan Kode

#### Palet warna
```python
BG        = "#F0F2F5"   # Abu abu muda — background utama
BG2       = "#FFFFFF"   # Putih — panel/card
ACCENT    = "#1A56DB"   # Biru tua — tombol utama
GREEN     = "#057A55"   # Hijau tua — sukses
RED       = "#C81E1E"   # Merah tua — error
YELLOW    = "#92400E"   # Amber tua — warning
TEXT      = "#111827"   # Hitam — teks utama
CANVAS_BG = "#1F2937"   # Gelap — canvas animasi
```
Tema terang dengan teks gelap untuk kontras tinggi. Canvas animasi sengaja dibuat gelap agar paket berwarna kelihatan jelas.

#### `AnimatedCanvas` — Canvas dengan animasi real-time
```python
class AnimatedCanvas:
    def __init__(self, parent, layout_builder):
        self.canvas.bind("<Configure>", self._on_resize)
        self._animate()

    def _on_resize(self, event):
        w, h = event.width, event.height
        self.topology = self.layout_builder(w, h)   # Rebuild topologi sesuai ukuran baru

    def _animate(self):
        self.canvas.delete("all")
        self._draw_grid(w, h)
        self._draw_links()
        self._draw_nodes()
        for p in self.packets:
            p.update_position()
        self._draw_packets()
        self.packets = [p for p in self.packets if not p.is_done]
        self.canvas.after(30, self._animate)   # Loop setiap 30ms (~33 FPS)
```
`layout_builder` adalah fungsi yang menerima `(width, height)` dan mengembalikan `SystemTopology`. Setiap kali window di-resize, event `<Configure>` terpanggil dan topologi dibangun ulang dengan ukuran baru — itulah yang membuat posisi node selalu terpusat dan proporsional.

Loop animasi berjalan di main thread menggunakan `canvas.after(30, ...)` — Tkinter menjalankan `_animate` setiap 30 milidetik tanpa memblokir GUI.

#### `LogPanel` — Panel log berwarna
```python
class LogPanel:
    def append(self, msg: str):
        tag = ("ok"   if "✓" in msg else
               "err"  if "✗" in msg or "ERROR" in msg or "TIMEOUT" in msg else
               "warn" if "⚠" in msg else "info")
        self.text.insert("end", msg + "\n", tag)
```
Log ditampilkan dengan warna berbeda: biru untuk info, hijau untuk sukses (✓), merah untuk error (✗), kuning untuk peringatan (⚠).

#### `MetricCard` — Kartu statistik
```python
class MetricCard:
    def __init__(self, parent, label, color):
        tk.Label(frame, text=label, ...).pack()
        self.val = tk.Label(frame, text="0", fg=color, font=("Consolas", 15, "bold"))
        self.val.pack()

    def set(self, value):
        self.val.config(text=str(value))
```
Kartu kecil yang menampilkan satu angka statistik. `set()` dipanggil setiap kali ada event komunikasi baru.

#### Empat kelas tab
| Kelas | Tab GUI | Model yang ditampilkan |
|---|---|---|
| `RequestResponseTab` | Tab 1 | Request-Response |
| `PubSubTab` | Tab 2 | Publish-Subscribe |
| `MessagePassingTab` | Tab 3 | Message Passing |
| `RPCTab` | Tab 4 | RPC |

Setiap kelas tab memiliki struktur yang sama:
1. Deskripsi singkat model di bagian atas
2. Canvas animasi (mengambil sebagian besar ruang)
3. Baris kartu metrik
4. Baris kontrol (tombol, slider, dropdown)
5. Panel log di bagian bawah

---

## File 7: `main.py`

### Fungsi File
Entry point program. Membuat jendela utama Tkinter, menginisialisasi semua tab, dan membangun tab Perbandingan yang menampilkan metrik dari semua model secara berdampingan.

### Isi dan Penjelasan Kode

#### Membuat jendela utama
```python
def main():
    root = tk.Tk()
    root.geometry("860x700")
    root.minsize(700, 580)      # Ukuran minimum — tidak bisa lebih kecil dari ini
    root.resizable(True, True)  # Bisa di-resize ke semua arah
```

#### Inisialisasi semua tab
```python
    rr_tab  = RequestResponseTab(notebook)
    ps_tab  = PubSubTab(notebook)
    mp_tab  = MessagePassingTab(notebook)
    rpc_tab = RPCTab(notebook)
    build_comparison_tab(notebook, tabs)
```

#### `build_comparison_tab` — Tab perbandingan metrik
```python
def build_comparison_tab(notebook, tabs):
    def refresh():
        rr  = tabs["rr"].sim.get_metrics()
        ps  = tabs["ps"].sim.get_metrics()
        mp  = tabs["mp"].sim.get_metrics()
        rpc = tabs["rpc"].sim.get_metrics()
        # Update tabel dan bar chart
```
Tab ini **tidak otomatis update** — pengguna harus klik tombol "Refresh Data" setelah menjalankan simulasi di tab-tab lain. Ini disengaja agar pengguna bisa membandingkan pada kondisi yang diinginkan.

Tabel perbandingan menampilkan 7 kolom: Model, Total Msg, Sukses, Gagal/Timeout, Avg Latency/RTT, Coupling, Sinkron.

Bar chart dibuat responsif — lebar setiap bar dihitung dari lebar window saat itu:
```python
W = bar_canvas.winfo_width()
bar_w = (W - 2*margin - gap*(n-1)) // n
```

#### Cleanup saat window ditutup
```python
    def on_close():
        mp_tab.sim.stop_all()       # Hentikan semua worker thread Message Passing
        for tab in [rr_tab, ps_tab, mp_tab, rpc_tab]:
            tab.anim.stop()         # Hentikan loop animasi
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
```
Penting untuk menghentikan semua thread dan loop animasi sebelum menutup window, agar program benar-benar berhenti tanpa ada thread yang masih jalan di background.

---

## Panduan Interaksi Pengguna

### Tab Request-Response
| Elemen | Fungsi |
|---|---|
| Field **Payload** | Isi pesan yang dikirim, contoh: `GET /user/data` |
| Slider **Latency** | Atur waktu respons server: 100ms (cepat) sampai 2000ms (lambat) |
| Tombol **Kirim Request** | Kirim satu request, lihat animasi paket biru bergerak |
| Tombol **Reset** | Hapus semua statistik dan log, mulai dari awal |

### Tab Publish-Subscribe
| Elemen | Fungsi |
|---|---|
| Dropdown **Publisher** | Pilih Publisher-1 atau Publisher-2 sebagai pengirim |
| Dropdown **Topic** | Pilih topic: `orders`, `payments`, atau `alerts` |
| Field **Pesan** | Isi konten pesan yang dipublish |
| Tombol **Publish** | Publish pesan, lihat animasi menyebar ke subscriber |
| Tombol **+ Subscriber** | Tambah subscriber baru (maks 6) secara real-time |

### Tab Message Passing
| Elemen | Fungsi |
|---|---|
| Dropdown **Dari / Ke** | Pilih pasangan node pengirim dan penerima |
| Dropdown **Priority** | 1=normal, 2=high, 3=urgent (urgent diproses lebih dulu) |
| Field **Isi** | Konten pesan yang dikirim |
| Tombol **Kirim** | Masukkan pesan ke queue, lihat animasi ke queue lalu ke node tujuan |

### Tab RPC
| Elemen | Fungsi |
|---|---|
| Dropdown **Prosedur** | Pilih fungsi yang dipanggil: `getUser`, `calcPrice`, `sendNotification`, `processOrder` |
| Slider **Network delay** | Atur delay jaringan: jika >2000ms akan terjadi **TIMEOUT** |
| Tombol **Panggil RPC** | Panggil prosedur, lihat animasi chain 4 langkah |

### Tab Perbandingan
| Elemen | Fungsi |
|---|---|
| Tabel metrik | Menampilkan data dari semua tab berdampingan |
| Bar chart | Visualisasi perbandingan total pesan tiap model |
| Tombol **Refresh Data** | Ambil data terbaru dari semua simulasi dan update tampilan |

---

## Cara Membaca Hasil Simulasi

| Metrik | Lokasi | Cara baca |
|---|---|---|
| Total Request / Pemanggilan | Kartu metrik tiap tab | Makin banyak = makin banyak komunikasi yang terjadi |
| Sukses | Kartu hijau | Berhasil diproses oleh server/subscriber/node |
| Error / Timeout | Kartu merah | Error acak (RR) atau timeout karena delay terlalu besar (RPC) |
| Avg Latency / RTT | Kartu kuning | Rata-rata waktu dari kirim hingga terima response dalam ms |
| Di Queue | Kartu kuning (MP) | Pesan menunggu di antrian — jika terus naik berarti consumer kewalahan |
| Throughput /s | Kartu Pub-Sub | Berapa pesan per detik yang dipublikasikan sejak awal simulasi |
| Log hijau ✓ | Panel log | Komunikasi berhasil |
| Log merah ✗ | Panel log | Komunikasi gagal / timeout |
| Log kuning ⚠ | Panel log | Peringatan (queue penuh, subscriber maks) |