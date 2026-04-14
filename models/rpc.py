import time
import json
import threading
import random
from dataclasses import dataclass, field
from typing import Any, Optional, Callable


@dataclass
class RPCRequest:
    call_id: str
    procedure: str
    args: dict
    caller: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class RPCResponse:
    call_id: str
    procedure: str
    result: Any
    status: str          # "SUCCESS", "TIMEOUT", "ERROR"
    error_msg: str = ""
    execution_time_ms: float = 0.0
    rtt_ms: float = 0.0


class RPCServer:
    def __init__(self, name: str):
        self.name = name
        self._procedures: dict[str, Callable] = {}
        self.calls_received = 0
        self.calls_success = 0
        self.calls_error = 0
        self.log: list[str] = []
        self._register_default_procedures()

    def _register_default_procedures(self):
        def get_user(user_id: int) -> dict:
            users = {
                1: {"id": 1, "name": "Andi Pratama", "role": "admin"},
                2: {"id": 2, "name": "Budi Santoso", "role": "user"},
                3: {"id": 3, "name": "Citra Dewi",   "role": "moderator"},
            }
            if user_id not in users:
                raise ValueError(f"User ID {user_id} tidak ditemukan")
            return users[user_id]

        def calc_price(quantity: int, unit_price: float) -> dict:
            subtotal = quantity * unit_price
            tax = subtotal * 0.11   # PPN 11%
            total = subtotal + tax
            return {"subtotal": subtotal, "tax": tax, "total": round(total, 2)}

        def send_notification(email: str, message: str) -> dict:
            if "@" not in email:
                raise ValueError(f"Email tidak valid: {email}")
            return {"status": "sent", "recipient": email, "msg_id": f"notif-{random.randint(1000,9999)}"}

        def process_order(product_id: int, quantity: int, customer: str) -> dict:
            time.sleep(0.1)   # Simulasi proses lebih berat
            order_id = f"ORD-{random.randint(10000,99999)}"
            return {"order_id": order_id, "product_id": product_id,
                    "quantity": quantity, "customer": customer, "status": "CREATED"}

        self._procedures = {
            "getUser":          get_user,
            "calcPrice":        calc_price,
            "sendNotification": send_notification,
            "processOrder":     process_order,
        }

    def register_procedure(self, name: str, func: Callable):
        #Daftarkan prosedur baru ke server
        self._procedures[name] = func
        self.log.append(f"[RPC SERVER {self.name}] Prosedur '{name}' terdaftar")

    def execute(self, request: RPCRequest, network_delay_ms: float = 100) -> RPCResponse:
        #Terima RPC request, eksekusi prosedur, dan kembalikan hasilnya. network_delay_ms mensimulasikan latency jaringan dua arah.
        self.calls_received += 1
        self.log.append(
            f"[RPC SERVER {self.name}] Menerima call#{request.call_id}: "
            f"{request.procedure}({json.dumps(request.args)})"
        )

        # Simulasi network delay (dari client ke server)
        time.sleep(network_delay_ms / 2 / 1000)

        t_start = time.time()

        if request.procedure not in self._procedures:
            self.calls_error += 1
            self.log.append(f"[RPC SERVER {self.name}] ✗ Prosedur '{request.procedure}' tidak ada")
            time.sleep(network_delay_ms / 2 / 1000)   # Delay balik
            return RPCResponse(
                call_id=request.call_id,
                procedure=request.procedure,
                result=None,
                status="ERROR",
                error_msg=f"Procedure '{request.procedure}' not found"
            )

        try:
            func = self._procedures[request.procedure]
            result = func(**request.args)
            exec_time = (time.time() - t_start) * 1000
            self.calls_success += 1
            self.log.append(
                f"[RPC SERVER {self.name}] ✓ {request.procedure} selesai "
                f"({exec_time:.0f}ms) → {json.dumps(result)}"
            )
            # Simulasi network delay (dari server ke client)
            time.sleep(network_delay_ms / 2 / 1000)
            return RPCResponse(
                call_id=request.call_id,
                procedure=request.procedure,
                result=result,
                status="SUCCESS",
                execution_time_ms=exec_time
            )
        except Exception as e:
            exec_time = (time.time() - t_start) * 1000
            self.calls_error += 1
            self.log.append(f"[RPC SERVER {self.name}] ✗ Error: {str(e)}")
            time.sleep(network_delay_ms / 2 / 1000)
            return RPCResponse(
                call_id=request.call_id,
                procedure=request.procedure,
                result=None,
                status="ERROR",
                error_msg=str(e),
                execution_time_ms=exec_time
            )

    @property
    def available_procedures(self) -> list[str]:
        return list(self._procedures.keys())


class RPCClient:
    #Komponen RPC Client — memanggil prosedur remote seolah fungsi lokal. Menangani marshalling argumen dan timeout.
    def __init__(self, name: str, server: RPCServer, timeout_ms: float = 2000):
        self.name = name
        self.server = server
        self.timeout_ms = timeout_ms
        self.call_count = 0
        self.success_count = 0
        self.timeout_count = 0
        self.error_count = 0
        self.rtts: list[float] = []
        self.log: list[str] = []

    def call(self, procedure: str, network_delay_ms: float = 200, **kwargs) -> RPCResponse:
        self.call_count += 1
        call_id = f"CALL-{self.call_count:04d}"

        request = RPCRequest(
            call_id=call_id,
            procedure=procedure,
            args=kwargs,
            caller=self.name
        )

        self.log.append(
            f"[RPC CLIENT {self.name}] Memanggil {procedure}({json.dumps(kwargs)}) "
            f"[timeout={self.timeout_ms}ms, delay={network_delay_ms}ms]"
        )

        # Jalankan di thread dengan timeout
        result_holder: list[RPCResponse] = []
        def _do_call():
            resp = self.server.execute(request, network_delay_ms)
            result_holder.append(resp)

        t_start = time.time()
        worker = threading.Thread(target=_do_call, daemon=True)
        worker.start()
        worker.join(timeout=self.timeout_ms / 1000)
        rtt = (time.time() - t_start) * 1000

        if not result_holder:
            # TIMEOUT
            self.timeout_count += 1
            self.log.append(
                f"[RPC CLIENT {self.name}] ✗ TIMEOUT call#{call_id}: "
                f"{procedure} melebihi {self.timeout_ms}ms"
            )
            return RPCResponse(
                call_id=call_id,
                procedure=procedure,
                result=None,
                status="TIMEOUT",
                error_msg=f"Timeout setelah {self.timeout_ms}ms",
                rtt_ms=rtt
            )

        response = result_holder[0]
        response.rtt_ms = rtt
        self.rtts.append(rtt)

        if response.status == "SUCCESS":
            self.success_count += 1
            self.log.append(
                f"[RPC CLIENT {self.name}] ✓ {procedure} sukses "
                f"[RTT={rtt:.0f}ms] → {json.dumps(response.result)}"
            )
        else:
            self.error_count += 1
            self.log.append(
                f"[RPC CLIENT {self.name}] ✗ {procedure} error: {response.error_msg}"
            )

        return response

    @property
    def avg_rtt(self) -> float:
        if not self.rtts:
            return 0.0
        return sum(self.rtts) / len(self.rtts)


class RPCSimulation:
    #Kelas utama simulasi RPC
    def __init__(self):
        self.server = RPCServer("RPC-Server-1")
        self.client = RPCClient("RPC-Client-1", self.server, timeout_ms=2000)

    def call(self, procedure: str, network_delay_ms: float = 200,
             callback=None, **kwargs):
        #Panggil RPC di thread terpisah agar GUI tidak freeze
        def _run():
            response = self.client.call(procedure, network_delay_ms, **kwargs)
            if callback:
                callback(response)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def get_metrics(self) -> dict:
        return {
            "total_calls":    self.client.call_count,
            "success":        self.client.success_count,
            "timeouts":       self.client.timeout_count,
            "errors":         self.client.error_count,
            "avg_rtt_ms":     round(self.client.avg_rtt, 1),
            "server_success": self.server.calls_success,
            "procedures":     self.server.available_procedures,
        }

    def get_logs(self) -> list[str]:
        return self.client.log + self.server.log

    def reset(self):
        self.server = RPCServer("RPC-Server-1")
        self.client = RPCClient("RPC-Client-1", self.server, timeout_ms=2000)