import time
import threading
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Callable


@dataclass
class Message:
    msg_id: str
    topic: str
    publisher: str
    content: str
    timestamp: float = field(default_factory=time.time)


class Broker:
    #Menyimpan daftar subscriber per topic dan mendistribusikan pesan.
    def __init__(self, name: str = "Broker-1"):
        self.name = name
        # topic -> list of (subscriber_name, callback)
        self._subscriptions: dict[str, list[tuple[str, Callable]]] = defaultdict(list)
        self.messages_received = 0
        self.messages_delivered = 0
        self.log: list[str] = []
        self.lock = threading.Lock()

    def subscribe(self, topic: str, subscriber_name: str, callback: Callable):
        with self.lock:
            self._subscriptions[topic].append((subscriber_name, callback))
        self.log.append(f"[BROKER] {subscriber_name} subscribe ke topic '{topic}'")

    def unsubscribe(self, topic: str, subscriber_name: str):
        #Hapus subscriber dari topic
        with self.lock:
            self._subscriptions[topic] = [
                (name, cb) for name, cb in self._subscriptions[topic]
                if name != subscriber_name
            ]
        self.log.append(f"[BROKER] {subscriber_name} unsubscribe dari topic '{topic}'")

    def publish(self, message: Message):
        """
        Terima pesan dari publisher dan distribusikan ke semua subscriber.
        Pengiriman ke tiap subscriber dilakukan di thread terpisah (asinkron).
        """
        with self.lock:
            subscribers = list(self._subscriptions.get(message.topic, []))

        self.messages_received += 1
        self.log.append(
            f"[BROKER] Menerima msg#{message.msg_id} topic='{message.topic}' "
            f"dari {message.publisher} — distribusi ke {len(subscribers)} subscriber"
        )

        if not subscribers:
            self.log.append(f"[BROKER] ⚠ Tidak ada subscriber untuk topic '{message.topic}'")
            return

        for sub_name, callback in subscribers:
            # Kirim ke tiap subscriber secara asinkron
            t = threading.Thread(target=self._deliver, args=(message, sub_name, callback), daemon=True)
            t.start()

    def _deliver(self, message: Message, sub_name: str, callback: Callable):
        """Kirim satu pesan ke satu subscriber."""
        time.sleep(0.05)   # Simulasi delay distribusi
        callback(message)
        self.messages_delivered += 1
        self.log.append(f"[BROKER] Dikirim ke {sub_name}")

    def get_topics(self) -> dict[str, int]:
        #Kembalikan daftar topic dan jumlah subscriber-nya.
        with self.lock:
            return {t: len(subs) for t, subs in self._subscriptions.items()}

    def subscriber_count(self, topic: str) -> int:
        with self.lock:
            return len(self._subscriptions.get(topic, []))


class Publisher:
    #mengirim pesan ke topic tanpa peduli siapa penerimanyqa
    def __init__(self, name: str, broker: Broker):
        self.name = name
        self.broker = broker
        self.publish_count = 0
        self.log: list[str] = []

    def publish(self, topic: str, content: str):
        self.publish_count += 1
        msg = Message(
            msg_id=f"MSG-{self.publish_count:04d}",
            topic=topic,
            publisher=self.name,
            content=content
        )
        self.log.append(f"[PUB {self.name}] Publish msg#{msg.msg_id} ke topic '{topic}': '{content}'")
        self.broker.publish(msg)    # Asinkron — publisher tidak menunggu


class Subscriber:
    #Komponen Subscriber, mendaftar ke topic dan menerima pesan dari broker
    def __init__(self, name: str, broker: Broker):
        self.name = name
        self.broker = broker
        self.received_messages: list[Message] = []
        self.subscribed_topics: list[str] = []
        self.log: list[str] = []

    def subscribe(self, topic: str):
        self.subscribed_topics.append(topic)
        self.broker.subscribe(topic, self.name, self._on_message)

    def unsubscribe(self, topic: str):
        if topic in self.subscribed_topics:
            self.subscribed_topics.remove(topic)
        self.broker.unsubscribe(topic, self.name)

    def _on_message(self, message: Message):
        #Callback yang dipanggil broker saat ada pesan masuk
        self.received_messages.append(message)
        self.log.append(
            f"[SUB {self.name}]  Terima msg#{message.msg_id} "
            f"dari topic '{message.topic}': '{message.content}'"
        )


class PubSubSimulation:
    #Kelas utama simulasi Publish-Subscribe
    def __init__(self):
        self.broker = Broker()
        self.publishers: list[Publisher] = []
        self.subscribers: list[Subscriber] = []
        self._setup_default()

    def _setup_default(self):
        #Setup awal: 2 publisher, 3 subscriber, beberapa topic
        p1 = Publisher("Publisher-1", self.broker)
        p2 = Publisher("Publisher-2", self.broker)
        self.publishers = [p1, p2]

        s1 = Subscriber("Subscriber-1", self.broker)
        s2 = Subscriber("Subscriber-2", self.broker)
        s3 = Subscriber("Subscriber-3", self.broker)
        self.subscribers = [s1, s2, s3]

        # Subscribe ke topic
        s1.subscribe("orders")
        s1.subscribe("payments")
        s2.subscribe("orders")
        s2.subscribe("alerts")
        s3.subscribe("payments")
        s3.subscribe("alerts")

    def publish(self, publisher_index: int, topic: str, content: str, callback=None):
        #Publish pesan dari publisher tertentu
        def _run():
            pub = self.publishers[publisher_index]
            pub.publish(topic, content)
            if callback:
                time.sleep(0.2)
                callback()

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def add_subscriber(self, name: str, topics: list[str]):
        #Tambah subscriber baru secara dinamis
        sub = Subscriber(name, self.broker)
        for topic in topics:
            sub.subscribe(topic)
        self.subscribers.append(sub)

    def get_metrics(self) -> dict:
        total_received = sum(len(s.received_messages) for s in self.subscribers)
        return {
            "total_published": sum(p.publish_count for p in self.publishers),
            "total_delivered": self.broker.messages_delivered,
            "active_subscribers": len(self.subscribers),
            "topics": self.broker.get_topics(),
        }

    def get_logs(self) -> list[str]:
        logs = list(self.broker.log)
        for p in self.publishers:
            logs += p.log
        for s in self.subscribers:
            logs += s.log
        return sorted(logs)

    def reset(self):
        self.broker = Broker()
        self.publishers.clear()
        self.subscribers.clear()
        self._setup_default()