import time
import queue
import threading
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueueMessage:
    msg_id: str
    sender: str
    receiver: str
    content: str
    priority: int = 1                          # 1=normal, 2=high, 3=urgent
    enqueue_time: float = field(default_factory=time.time)
    process_time: Optional[float] = None


class MessageQueue:
    #Komponen Queue — buffer antrian pesan antara pengirim dan penerima. Menggunakan PriorityQueue sehingga pesan urgent didahulukan.
    def __init__(self, name: str, maxsize: int = 20):
        self.name = name
        # PriorityQueue: (priority_inverted, timestamp, message)
        # priority dibalik karena queue.PriorityQueue mengambil nilai terkecil duluan
        self._queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=maxsize)
        self.enqueue_count = 0
        self.dequeue_count = 0
        self.log: list[str] = []

    def put(self, message: QueueMessage) -> bool:
        #Masukkan pesan ke queue. Return False jika queue penuh
        try:
            priority_key = (4 - message.priority, message.enqueue_time)   # Balik prioritas
            self._queue.put_nowait((priority_key, message))
            self.enqueue_count += 1
            self.log.append(
                f"[QUEUE {self.name}] ← Masuk: msg#{message.msg_id} "
                f"dari {message.sender} (priority={message.priority}) | size={self.size}"
            )
            return True
        except queue.Full:
            self.log.append(f"[QUEUE {self.name}] ⚠ PENUH! Pesan dari {message.sender} ditolak")
            return False

    def get(self, timeout: float = 1.0) -> Optional[QueueMessage]:
        #Ambil pesan dari queue. Blocking sampai ada pesan atau timeout
        try:
            _, message = self._queue.get(timeout=timeout)
            message.process_time = time.time()
            self.dequeue_count += 1
            wait_ms = (message.process_time - message.enqueue_time) * 1000
            self.log.append(
                f"[QUEUE {self.name}] Keluar: msg#{message.msg_id} "
                f"ke {message.receiver} | wait={wait_ms:.0f}ms"
            )
            return message
        except queue.Empty:
            return None

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def is_empty(self) -> bool:
        return self._queue.empty()


class Node:
    #Komponen Node — entitas dalam sistem yang bisa mengirim dan menerima pesan. Setiap node memiliki queue inbox sendiri.
    def __init__(self, name: str, process_time_ms: float = 300):
        self.name = name
        self.inbox = MessageQueue(f"{name}-inbox")
        self.process_time_ms = process_time_ms
        self.sent_count = 0
        self.received_count = 0
        self.processed_messages: list[QueueMessage] = []
        self.log: list[str] = []
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

    def send(self, message: QueueMessage, target_node: 'Node') -> bool:
        #Kirim pesan ke inbox node lain
        self.sent_count += 1
        self.log.append(f"[NODE {self.name}] → Kirim msg#{message.msg_id} ke {target_node.name}")
        return target_node.inbox.put(message)

    def start_processing(self, callback=None):
        self._running = True
        def _worker():
            while self._running:
                msg = self.inbox.get(timeout=0.5)
                if msg:
                    self._process_message(msg, callback)

        self._worker_thread = threading.Thread(target=_worker, daemon=True)
        self._worker_thread.start()

    def stop_processing(self):
        self._running = False

    def _process_message(self, message: QueueMessage, callback=None):
        #Proses satu pesan simulasi kerja dengan sleep
        self.log.append(f"[NODE {self.name}] ⚙ Memproses msg#{message.msg_id}: '{message.content}'")
        time.sleep(self.process_time_ms / 1000)   # Simulasi pemrosesan
        self.received_count += 1
        self.processed_messages.append(message)
        self.log.append(f"[NODE {self.name}] Selesai proses msg#{message.msg_id}")
        if callback:
            callback(message, self.name)


class MessagePassingSimulation:
    #Kelas utama simulasi Message Passing dengan topologi bintang (semua ke semua via queue)
    def __init__(self):
        self.nodes: list[Node] = []
        self.message_counter = 0
        self._setup_default()

    def _setup_default(self):
        #Setup 4 node: A, B, C, D — masing-masing dengan kecepatan proses berbeda
        self.nodes = [
            Node("Node-A", process_time_ms=200),
            Node("Node-B", process_time_ms=400),
            Node("Node-C", process_time_ms=150),
            Node("Node-D", process_time_ms=500),
        ]

    def start_all(self, callback=None):
        #Aktifkan semua node agar siap menerima dan memproses pesan
        for node in self.nodes:
            node.start_processing(callback)

    def stop_all(self):
        for node in self.nodes:
            node.stop_processing()

    def send_message(self, from_idx: int, to_idx: int, content: str, priority: int = 1) -> bool:
        #Kirim pesan dari satu node ke node lain
        if from_idx == to_idx:
            return False
        self.message_counter += 1
        sender = self.nodes[from_idx]
        receiver = self.nodes[to_idx]

        msg = QueueMessage(
            msg_id=f"MP-{self.message_counter:04d}",
            sender=sender.name,
            receiver=receiver.name,
            content=content,
            priority=priority
        )
        return sender.send(msg, receiver)

    def get_metrics(self) -> dict:
        total_sent = sum(n.sent_count for n in self.nodes)
        total_recv = sum(n.received_count for n in self.nodes)
        total_queue = sum(n.inbox.size for n in self.nodes)
        return {
            "total_sent": total_sent,
            "total_processed": total_recv,
            "queue_depth": total_queue,
            "node_stats": [
                {"name": n.name, "sent": n.sent_count,
                 "received": n.received_count, "queue": n.inbox.size}
                for n in self.nodes
            ]
        }

    def get_logs(self) -> list[str]:
        logs = []
        for node in self.nodes:
            logs += node.log
            logs += node.inbox.log
        return logs

    def reset(self, callback=None):
        self.stop_all()
        self.message_counter = 0
        self._setup_default()
        self.start_all(callback)