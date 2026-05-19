
####################################################
# DVrouter.py
# Name:
# HUID:
#####################################################

from router import Router
from packet import Packet
import json


class DVrouter(Router):
    """Distance vector routing protocol implementation."""

    INFINITY = 16

    def __init__(self, addr, heartbeat_time):
        Router.__init__(self, addr)

        self.heartbeat_time = heartbeat_time
        self.last_time = 0

        # port -> (neighbor_addr, cost)
        self.taitai = {}

        # destination -> cost
        self.distance_vector = {self.addr: 0}

        # destination -> port
        self.forwarding_table = {}

        # neighbor -> advertised DV
        self.neighbor_vectors = {}

    def broadcast_vector(self):
        """Send this router's distance vector to all neighbors."""
        content = json.dumps({
            "sender": self.addr,
            "vector": self.distance_vector
        })

        for port in self.taitai:
            pkt = Packet(
                kind=Packet.ROUTING,
                src_addr=self.addr,
                dst_addr=0,
                content=content
            )
            self.send(port, pkt)

    def recompute_routes(self):
        """Recompute shortest paths using Bellman-Ford."""
        new_dv = {self.addr: 0}
        new_ft = {}

        # Direct neighbors
        for port, (neighbor, cost) in self.taitai.items():
            if cost < new_dv.get(neighbor, self.INFINITY):
                new_dv[neighbor] = cost
                new_ft[neighbor] = port

        # Routes learned from neighbors
        for port, (neighbor, link_cost) in self.taitai.items():
            neighbor_vector = self.neighbor_vectors.get(neighbor, {})

            for dest, neighbor_cost in neighbor_vector.items():

                if dest == self.addr:
                    continue

                total_cost = min(
                    self.INFINITY,
                    link_cost + neighbor_cost
                )

                if total_cost < new_dv.get(dest, self.INFINITY):
                    new_dv[dest] = total_cost
                    new_ft[dest] = port

        changed = (
            new_dv != self.distance_vector or
            new_ft != self.forwarding_table
        )

        self.distance_vector = new_dv
        self.forwarding_table = new_ft

        return changed

    def handle_packet(self, port, packet):
        """Process incoming packet."""

        if packet.is_traceroute:
            # Forward normal data packets
            if packet.dst_addr in self.forwarding_table:
                out_port = self.forwarding_table[packet.dst_addr]
                self.send(out_port, packet)

        else:
            # Routing packet
            data = json.loads(packet.content)

            sender = data["sender"]
            vector = data["vector"]

            changed = False

            if sender not in self.neighbor_vectors:
                changed = True
            elif self.neighbor_vectors[sender] != vector:
                changed = True

            self.neighbor_vectors[sender] = vector

            if changed:
                updated = self.recompute_routes()

                if updated:
                    self.broadcast_vector()

    def handle_new_link(self, port, endpoint, cost):
        """Handle new link."""

        self.taitai[port] = (endpoint, cost)

        # Direct route to neighbor
        self.distance_vector[endpoint] = cost
        self.forwarding_table[endpoint] = port

        updated = self.recompute_routes()

        if updated:
            self.broadcast_vector()

    def handle_remove_link(self, port):
        """Handle removed link."""

        if port not in self.taitai:
            return

        endpoint, _ = self.taitai[port]

        del self.taitai[port]

        if endpoint in self.neighbor_vectors:
            del self.neighbor_vectors[endpoint]

        updated = self.recompute_routes()

        if updated:
            self.broadcast_vector()

    def handle_time(self, time_ms):
        """Handle current time."""

        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms

            # Periodic DV broadcast
            self.broadcast_vector()

    def __repr__(self):
        """Representation for debugging in the network visualizer."""

        return (
            f"DVrouter(addr={self.addr}, "
            f"dv={self.distance_vector}, "
            f"ft={self.forwarding_table})"
        )
