import sys
import socket
import threading
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from blockchain import Blockchain
from socket_helper import SocketHelper
from block import Block
import time
from collections import deque
from enums import State

MAX_QUEUED_CONNECTIONS = 5

class Peer:
    def __init__(self, tracker_addr, tracker_port, listening_port, transaction_file=None):
        self.listening_port = listening_port
        self.tracker_addr = tracker_addr
        self.tracker_port = tracker_port
        self.tracker_lock = threading.Lock()

        self.send_lock = threading.Lock()

        self.rcv_buffer_lock = threading.Lock()
        self.rcv_buffer = deque()
        self.state = State.IDLE

        self.listening_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listening_sock.bind(('', listening_port))
        self.listening_thread = threading.Thread(target=self.process_peer_connections, args=(self.listening_sock,))
        self.listening_thread.start()

        self.polling_thread = threading.Thread(target=self.poll_from_rcv_buffer)
        self.polling_thread.start()

        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.connect((tracker_addr, tracker_port))
        self.tracker_socket_helper = SocketHelper(self.tracker_socket)

        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        self.public_key = self.private_key.public_key()

        self.blockchain = Blockchain()

        
        # self.outgoing_messages
        # self.incoming_messages
        # self.transactions

        # self.send_thread
        # self.receive_thread
        # self.mine_thread

        # self.log_file

    def process_peer_connections(self, listening_sock):
        print("Started listening thread.")
        listening_sock.listen(MAX_QUEUED_CONNECTIONS)
        while True:
            peer_socket, addr = listening_sock.accept()
            peer_socket_helper = SocketHelper(peer_socket)
            header = peer_socket_helper.get_data_until_newline().decode()
            header_arr = header.split(' ')
            if header_arr[0] == "BLOCK":
                block_len = int(header_arr[1])
                block_encoded = peer_socket_helper.get_n_bytes_of_data(block_len)
                block_builder = Block()
                block = block_builder.from_bytes(block_encoded)

                self.rcv_buffer_lock.acquire()
                self.rcv_buffer.append({"type":"BLOCK", "tag":header_arr[2], "payload":block, "peer_addr": addr})
                self.rcv_buffer_lock.release()
            elif header_arr[0] == "GET-BLOCK":
                # TODO: Would want to grab the block ID from the header and use it to find the block on our chain to send back
                # TODO: Replace the dummy logic here with the above
                dummy_block = Block(_id=1, data="dummy", nonce=100, prev_hash=2, _hash=1)
                self.send_block_to_peer(block, "EXIST", peer_socket)
            else:
                print("Unsupported header type")

            peer_socket.close()

    def poll_from_rcv_buffer(self):
        while True:
            self.rcv_buffer_lock.acquire()
            if len(self.rcv_buffer) > 0:
                data = self.rcv_buffer.popleft()
            else:
                self.rcv_buffer_lock.release()
                continue

            self.rcv_buffer_lock.release()

            if data["type"] == "BLOCK":
                print(data)
                # TODO: Put it on the chain and do all that verification mumbo-jumbo
                fork = False # TODO: Add forking logic
                if fork:
                    # TODO: Send get block requests to all the peer nodes

                    # Set state to wait-mode where all we are looking for are
                    # get block responses
                    peer_nodes_serialized = self.request_nodes_from_tracker()
                    peer_nodes = self.parse_serialized_nodes()
                    peer_blocks = self.request_block_from_all_peers(peer_nodes, 100)
            else:
                print("rcv_buffer: got unsupported data type, ignoring")

            # To avoid throttling the CPU
            time.sleep(0.001)

    def request_block_from_all_peers(self, peer_nodes, block_id):
        peer_blocks = []
        self.send_lock.acquire()
        for node in peer_nodes:
            dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dest_socket.connect((node[0], node[1]))

            msg = ["GET-BLOCK", " ", str(block_id), "\n"]
            msg_bytes = "".join(msg).encode()

            dest_socket.sendall(msg_bytes)

            dest_socket_helper = SocketHelper(dest_socket)
            header = dest_socket_helper.get_data_until_newline().decode()

            header_arr = header.split(' ')
            block_len = int(header_arr[1])

            block_encoded = dest_socket_helper.get_n_bytes_of_data(block_len)
            block_builder = Block()
            block = block_builder.from_bytes(block_encoded)
            peer_blocks.append(block)

            print("Block retrieved from GET-BLOCK:", block.to_string())

            dest_socket.close()
        self.send_lock.release()
        return peer_blocks

    def send_join_message(self):
        join_msg = "".join(["JOIN\n", str(self.listening_port), "\n"])
        self.tracker_socket.sendall(join_msg.encode())

    def request_nodes_from_tracker(self):
        peer_request = "LIST\n"
        self.tracker_lock.acquire()

        self.tracker_socket.sendall(peer_request.encode())

        header_bytes = self.tracker_socket_helper.get_data_until_newline()
        header = header_bytes.decode()

        if header != "PEERS":
            print("Invalid header, expected PEERS")
            return None

        nodes = self.tracker_socket_helper.get_data_until_newline()

        self.tracker_lock.release()
        return nodes.decode()

    def parse_serialized_nodes(self, node_str):
        if len(node_str) == 0:
            return []

        nodes = node_str.split(' ')
        # Array of (IP Address, listening port)
        node_arr = []
        for node in nodes:
            pair = node.split(',')
            node_arr.append( (pair[0], int(pair[1])) )
        return node_arr

    def send_block_to_peer(self, block, tag, peer_socket):
        block_bytes = block.to_bytes()
        block_msg_header = ["BLOCK", " ", str(len(block_bytes)), " ", tag, "\n"]
        header_bytes = "".join(block_msg_header).encode()
        all_bytes = header_bytes + block_bytes + b'\n'
        peer_socket.sendall(all_bytes)

    def broadcast_block_to_all_peers(self, block):
        nodes_serialized = self.request_nodes_from_tracker()
        nodes = self.parse_serialized_nodes(nodes_serialized)

        self.send_lock.acquire()
        for node in nodes:
            dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dest_socket.connect((node[0], node[1]))
            
            self.send_block_to_peer(block, "NEW", dest_socket)

            dest_socket.close()
        self.send_lock.release()

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
    nodes = peer.parse_serialized_nodes(serialized_nodes)
    print(nodes)

    dummy_block = Block(_id=1, data="dummy", nonce=100, prev_hash=2, _hash=1)
    peer.broadcast_block_to_all_peers(dummy_block)
    peer.request_block_from_all_peers(nodes, 100)


