import time
import random
import threading
from dataclasses import dataclass, field
from typing import Optional


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
    status: str         
    data: str
    latency_ms: float
    timestamp: float = field(default_factory=time.time)


class Server:
    # Menerima request, memprosesnya, dan mengembalikan response.
    def __init__(self, name: str, error_rate: float = 0.2):
        self.name = name
        self.error_rate = error_rate       
        self.requests_received = 0
        self.responses_sent = 0
        self.log: list[str] = []

    def handle_request(self, request: Request, latency_ms: float = 500) -> Response:
        self.requests_received += 1
        self.log.append(f"[SERVER {self.name}] Menerima request#{request.request_id} dari {request.sender}")

        # Simulasi waktu pemrosesan
        time.sleep(latency_ms / 1000)

        # Simulasi kemungkinan error
        if random.random() < self.error_rate:
            resp = Response(
                request_id=request.request_id,
                status="ERROR",
                data="Internal Server Error",
                latency_ms=latency_ms
            )
            self.log.append(f"[SERVER {self.name}] ERROR memproses request#{request.request_id}")
        else:
            resp = Response(
                request_id=request.request_id,
                status="OK",
                data=f"Hasil dari: {request.payload}",
                latency_ms=latency_ms
            )
            self.log.append(f"[SERVER {self.name}] Sukses memproses request#{request.request_id}")

        self.responses_sent += 1
        return resp


class Client:
    def __init__(self, name: str):
        self.name = name
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_latency = 0.0
        self.log: list[str] = []

    def send_request(self, server: Server, payload: str, latency_ms: float = 500) -> Response:
        self.request_count += 1
        req_id = f"REQ-{self.request_count:04d}"

        request = Request(
            request_id=req_id,
            sender=self.name,
            receiver=server.name,
            payload=payload
        )

        self.log.append(f"[CLIENT {self.name}] Mengirim {req_id} → {server.name}: '{payload}'")

        t_start = time.time()
        response = server.handle_request(request, latency_ms)   # BLOCKING
        t_end = time.time()

        actual_latency = (t_end - t_start) * 1000
        self.total_latency += actual_latency

        if response.status == "OK":
            self.success_count += 1
            self.log.append(f"[CLIENT {self.name}] Response {req_id}: {response.data} ({actual_latency:.0f}ms)")
        else:
            self.error_count += 1
            self.log.append(f"[CLIENT {self.name}] Response {req_id}: {response.data} ({actual_latency:.0f}ms)")

        return response

    @property
    def avg_latency(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_latency / self.request_count


class RequestResponseSimulation:
    # Kelas utama simulasi Request-Response untuk menjalankan dan memantau simulasi
    def __init__(self):
        self.client = Client("Client-1")
        self.server = Server("Server-1", error_rate=0.2)
        self.history: list[dict] = []
        self.lock = threading.Lock()

    def run_once(self, payload: str = "GET /data", latency_ms: float = 500, callback=None):
        #jalankan satu siklus request-response di thread terpisah
        def _run():
            response = self.client.send_request(self.server, payload, latency_ms)
            with self.lock:
                self.history.append({
                    "id": response.request_id,
                    "status": response.status,
                    "latency": latency_ms,
                    "data": response.data
                })
            if callback:
                callback(response)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def get_metrics(self) -> dict:
        return {
            "total_requests": self.client.request_count,
            "success": self.client.success_count,
            "errors": self.client.error_count,
            "avg_latency_ms": round(self.client.avg_latency, 1),
            "server_received": self.server.requests_received,
        }

    def get_logs(self) -> list[str]:
        return self.client.log + self.server.log

    def reset(self):
        self.client = Client("Client-1")
        self.server = Server("Server-1", error_rate=0.2)
        self.history.clear()