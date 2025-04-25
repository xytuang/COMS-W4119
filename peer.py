import sys
import socket
import threading
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from socket_helper import SocketHelper

MAX_QUEUED_CONNECTIONS = 5

def process_peer_connections(listening_sock):
    print("Started listening thread.")
    listening_sock.listen(MAX_QUEUED_CONNECTIONS)
    while True:
        peer_socket, addr = listening_sock.accept()

        # Do stuff

class Peer:
    def __init__(self, tracker_addr, tracker_port, listening_port, transaction_file=None):
        self.listening_port = listening_port
        self.tracker_addr = tracker_addr
        self.tracker_port = tracker_port

        self.listening_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listening_sock.bind(('', listening_port))
        self.listening_thread = threading.Thread(target=process_peer_connections, args=(self.listening_sock,))
        self.listening_thread.start()

        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.connect((tracker_addr, tracker_port))
        self.tracker_socket_helper = SocketHelper(self.tracker_socket)

        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        self.public_key = self.private_key.public_key()

        # self.blockchain
        # self.public_key
        # self.private_key
        # self.state
        # self.outgoing_messages
        # self.incoming_messages
        # self.transactions

        # self.send_thread
        # self.receive_thread
        # self.mine_thread

        # self.log_file

    def send_join_message(self):
        join_msg = "".join(["JOIN\n", str(self.listening_port), "\n"])
        self.tracker_socket.sendall(join_msg.encode())

    def request_nodes_from_tracker(self):
        peer_request = "LIST\n"
        self.tracker_socket.sendall(peer_request.encode())

        header_bytes = self.tracker_socket_helper.get_data_until_newline()
        header = header_bytes.decode()

        if header != "PEERS":
            print("Invalid header, expected PEERS")
            return None

        nodes = self.tracker_socket_helper.get_data_until_newline()
        return nodes.decode()

    def parse_serialized_nodes(self, node_str):
        if len(node_str) == 0:
            return []

        nodes = node_str.split(' ')
        # Array of (IP Address, listening port)
        node_arr = []
        for node in nodes:
            pair = node.split(',')
            node_arr.append( (pair[0], pair[1]) )
        return node_arr

    def handle_send(self):
        pass
    
    def handle_receive(self):
        pass

    def handle_mine(self):
        pass

if __name__ == '__main__':
    listening_port = int(sys.argv[1])
    tracker_addr = sys.argv[2]
    tracker_port = int(sys.argv[3])

    peer = Peer(tracker_addr, tracker_port, listening_port)
    peer.send_join_message()

    serialized_nodes = peer.request_nodes_from_tracker()
    print(peer.parse_serialized_nodes(serialized_nodes))


