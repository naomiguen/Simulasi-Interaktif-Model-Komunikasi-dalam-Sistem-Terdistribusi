import time
import random
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class NodeType(Enum):
    CLIENT   = "Client"
    SERVER   = "Server"
    BROKER   = "Broker"
    DATABASE = "Database"
    DEVICE   = "Device"
    BALANCER = "Load Balancer"
    QUEUE    = "Queue"


class NodeStatus(Enum):
    ONLINE  = "online"
    OFFLINE = "offline"
    BUSY    = "busy"
    ERROR   = "error"


@dataclass
class SystemNode:
    node_id:    str
    name:       str
    node_type:  NodeType
    host:       str = "localhost"
    port:       int = 8080
    status:     NodeStatus = NodeStatus.ONLINE

    # Posisi di canvas GUI (untuk visualisasi)
    canvas_x:   float = 0.0
    canvas_y:   float = 0.0

    # Statistik operasional
    messages_sent:     int = 0
    messages_received: int = 0
    uptime_start:      float = field(default_factory=time.time)

    def send_message(self):
        self.messages_sent += 1

    def receive_message(self):
        self.messages_received += 1

    def set_status(self, status: NodeStatus):
        self.status = status

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self.uptime_start

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def to_dict(self) -> dict:
        return {
            "id":       self.node_id,
            "name":     self.name,
            "type":     self.node_type.value,
            "address":  self.address,
            "status":   self.status.value,
            "sent":     self.messages_sent,
            "received": self.messages_received,
        }


@dataclass
class Packet:
    packet_id:  str
    src_node:   SystemNode
    dst_node:   SystemNode
    content:    str
    color:      str = "#378ADD"   # Warna di canvas
    size:       int = 8           # Radius lingkaran di canvas

    # Progress animasi (0.0 = di src, 1.0 = di dst)
    progress:   float = 0.0
    speed:      float = 0.02      # Increment progress per frame

    # Posisi canvas saat ini (dihitung dari progress)
    current_x:  float = 0.0
    current_y:  float = 0.0

    model_type: str = "unknown"   # "rr", "ps", "mp", "rpc"
    is_return:  bool = False      # True jika ini paket response/return

    def update_position(self):
        #Hitung posisi saat ini berdasarkan progress (interpolasi linear)
        self.progress = min(1.0, self.progress + self.speed)
        self.current_x = self.src_node.canvas_x + (self.dst_node.canvas_x - self.src_node.canvas_x) * self.progress
        self.current_y = self.src_node.canvas_y + (self.dst_node.canvas_y - self.src_node.canvas_y) * self.progress

    @property
    def is_done(self) -> bool:
        return self.progress >= 1.0


@dataclass
class NetworkLink:
    #Representasi koneksi jaringan antara dua node. Dipakai untuk menggambar garis di canvas.
    src:       SystemNode
    dst:       SystemNode
    bandwidth: float = 100.0   # Mbps
    latency:   float = 10.0    # ms
    active:    bool  = True

    @property
    def is_congested(self) -> bool:
        return self.latency > 500


class SystemTopology:
    #Kelas yang mendefinisikan topologi lengkap sistem terdistribusi. Menyimpan semua node dan link, serta menyediakan layout per model.

    def __init__(self):
        self.nodes: dict[str, SystemNode] = {}
        self.links: list[NetworkLink] = []

    def add_node(self, node: SystemNode):
        self.nodes[node.node_id] = node

    def add_link(self, src_id: str, dst_id: str, latency: float = 10.0):
        src = self.nodes.get(src_id)
        dst = self.nodes.get(dst_id)
        if src and dst:
            self.links.append(NetworkLink(src=src, dst=dst, latency=latency))

    def get_node(self, node_id: str) -> Optional[SystemNode]:
        return self.nodes.get(node_id)

    def all_nodes(self) -> list[SystemNode]:
        return list(self.nodes.values())

    @staticmethod
    def build_request_response(canvas_w: int, canvas_h: int) -> 'SystemTopology':
        #Topologi untuk model Request-Response: Client ←→ Server (langsung, sinkron)
        topo = SystemTopology()
        cx, cy = canvas_w // 2, canvas_h // 2

        client = SystemNode("rr_client", "Client",   NodeType.CLIENT,   canvas_x=cx-200, canvas_y=cy)
        server = SystemNode("rr_server", "Server",   NodeType.SERVER,   canvas_x=cx+200, canvas_y=cy)
        db     = SystemNode("rr_db",     "Database", NodeType.DATABASE, canvas_x=cx+200, canvas_y=cy+110)

        topo.add_node(client)
        topo.add_node(server)
        topo.add_node(db)
        topo.add_link("rr_client", "rr_server", latency=100)
        topo.add_link("rr_server", "rr_db",     latency=20)
        return topo

    @staticmethod
    def build_pub_sub(canvas_w: int, canvas_h: int) -> 'SystemTopology':
        #Topologi untuk model Pub-Sub: Publisher → Broker → [Sub1, Sub2, Sub3]

        topo = SystemTopology()
        cx, cy = canvas_w // 2, canvas_h // 2

        pub1   = SystemNode("ps_pub1",  "Publisher-1",  NodeType.CLIENT,  canvas_x=80,       canvas_y=cy-50)
        pub2   = SystemNode("ps_pub2",  "Publisher-2",  NodeType.CLIENT,  canvas_x=80,       canvas_y=cy+50)
        broker = SystemNode("ps_broker","Broker",       NodeType.BROKER,  canvas_x=cx,       canvas_y=cy)
        sub1   = SystemNode("ps_sub1",  "Subscriber-1", NodeType.CLIENT,  canvas_x=cx+210,   canvas_y=cy-90)
        sub2   = SystemNode("ps_sub2",  "Subscriber-2", NodeType.CLIENT,  canvas_x=cx+210,   canvas_y=cy)
        sub3   = SystemNode("ps_sub3",  "Subscriber-3", NodeType.CLIENT,  canvas_x=cx+210,   canvas_y=cy+90)

        for n in [pub1, pub2, broker, sub1, sub2, sub3]:
            topo.add_node(n)

        topo.add_link("ps_pub1", "ps_broker")
        topo.add_link("ps_pub2", "ps_broker")
        topo.add_link("ps_broker", "ps_sub1")
        topo.add_link("ps_broker", "ps_sub2")
        topo.add_link("ps_broker", "ps_sub3")
        return topo

    @staticmethod
    def build_message_passing(canvas_w: int, canvas_h: int) -> 'SystemTopology':
        #Topologi untuk Message Passing: 4 Node + 1 Queue di tengah
        topo = SystemTopology()
        cx, cy = canvas_w // 2, canvas_h // 2

        node_a = SystemNode("mp_a", "Node-A", NodeType.CLIENT, canvas_x=cx-190, canvas_y=cy-80)
        node_b = SystemNode("mp_b", "Node-B", NodeType.CLIENT, canvas_x=cx+190, canvas_y=cy-80)
        node_c = SystemNode("mp_c", "Node-C", NodeType.CLIENT, canvas_x=cx-190, canvas_y=cy+80)
        node_d = SystemNode("mp_d", "Node-D", NodeType.CLIENT, canvas_x=cx+190, canvas_y=cy+80)
        q      = SystemNode("mp_q", "Queue",  NodeType.QUEUE,  canvas_x=cx,     canvas_y=cy)

        for n in [node_a, node_b, node_c, node_d, q]:
            topo.add_node(n)

        for nid in ["mp_a","mp_b","mp_c","mp_d"]:
            topo.add_link(nid, "mp_q")
            topo.add_link("mp_q", nid)
        return topo

    @staticmethod
    def build_rpc(canvas_w: int, canvas_h: int) -> 'SystemTopology':
        #Topologi untuk RPC: Client → Stub → (Network) → Skeleton → Server
        
        topo = SystemTopology()
        cx, cy = canvas_w // 2, canvas_h // 2

        client   = SystemNode("rpc_client",   "Client",   NodeType.CLIENT,   canvas_x=60,     canvas_y=cy)
        stub     = SystemNode("rpc_stub",     "Stub",     NodeType.CLIENT,   canvas_x=cx-100, canvas_y=cy)
        skeleton = SystemNode("rpc_skeleton", "Skeleton", NodeType.SERVER,   canvas_x=cx+100, canvas_y=cy)
        server   = SystemNode("rpc_server",   "Server",   NodeType.SERVER,   canvas_x=canvas_w-60, canvas_y=cy)

        for n in [client, stub, skeleton, server]:
            topo.add_node(n)

        topo.add_link("rpc_client",   "rpc_stub")
        topo.add_link("rpc_stub",     "rpc_skeleton")
        topo.add_link("rpc_skeleton", "rpc_server")
        return topo