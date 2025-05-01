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
from transaction import Transaction
import json

MAX_QUEUED_CONNECTIONS = 5

class Peer:
    def __init__(self, tracker_addr, tracker_port, listening_port, difficulty=4, vote_file=None, debug=False):
        self.listening_port = listening_port
        self.tracker_addr = tracker_addr
        self.tracker_port = tracker_port
        self.tracker_lock = threading.Lock()

        self.send_lock = threading.Lock()

        self.rcv_buffer_lock = threading.Lock()
        self.rcv_buffer = deque()

        self.state_lock = threading.Lock()
        self.state = State.IDLE

        self.debug = debug

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
        self.blockchain_lock = threading.Lock()

        self.txns = deque()
        self.txn_lock = threading.Lock()

        self.difficulty = difficulty

        self.mining_thread = threading.Thread(target=self.mine)
        self.mining_thread.start()

    def read_from_vote_file(self, vote_file):
        if not vote_file:
            return []

        votes = []
        with open(vote_file, "r") as f:
            for line in f:
                if line.strip():
                    votes.append(line.strip())
        print("votes", votes)
        return votes

    def public_key_to_bytes(self):
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_key_bytes

    def process_peer_connections(self, listening_sock):
        print("Started listening thread.")
        listening_sock.listen(MAX_QUEUED_CONNECTIONS)
        while True:
            peer_socket, addr = listening_sock.accept()
            peer_socket_helper = SocketHelper(peer_socket)
            print("process_peer_connections: Connected to new peer.")
            header = peer_socket_helper.get_data_until_newline().decode()
            header_arr = header.split(' ')
            print("process_peer_connections: found header", header_arr)
            if header_arr[0] == "BLOCK":
                block_len = int(header_arr[1])
                block_encoded = peer_socket_helper.get_n_bytes_of_data(block_len)
                block_builder = Block()
                block = block_builder.from_bytes(block_encoded)

                self.rcv_buffer_lock.acquire()
                self.rcv_buffer.append({"type":"BLOCK", "tag":header_arr[2], "payload":block, "peer_ip_addr": addr[0]})
                self.rcv_buffer_lock.release()
            elif header_arr[0] == "GET-BLOCK":
                # TODO: Would want to grab the block ID from the header and use it to find the block on our chain to send back
                # TODO: Replace the dummy logic here with the above
                _id = int(header_arr[1])
                with self.blockchain_lock:
                    requested_block = self.blockchain.get_block_by_id(_id)
                    
                    # If our chain is empty, create a fake block
                    if not requested_block:
                        fake_txn = Transaction(b"", time.time(), {})
                        fake_txn.sign(self.private_key)
                        requested_block = Block(-1, [fake_txn], 0, 0, 0, time.time())

                self.send_block_to_peer(requested_block, "EXIST", peer_socket)
            else:
                print("Unsupported header type")

            peer_socket.close()

    def poll_from_rcv_buffer(self):
        while True:
            data = None
            self.rcv_buffer_lock.acquire()
            if len(self.rcv_buffer) > 0:
                data = self.rcv_buffer.popleft()

            self.rcv_buffer_lock.release()

            if data == None:
                continue

            if data["type"] == "BLOCK":
                print(data)

                block = data["payload"]
                _id = block.id

                if not block.is_valid(self.difficulty):
                    continue

                with self.blockchain_lock:
                    latest_block = self.blockchain.get_latest_block()

                    # Hash matches and the block ID is the next expected one
                    if self.blockchain.can_add_block_to_chain(block):
                        print(f"added block {block.id} to chain")
                        self.blockchain.add_block(block)
                    # If the incoming block is valid and has more work done, potential fork
                    elif _id > len(self.blockchain.chain):
                        print("Forking")
                        # Forking logic :)
                        # Set state to wait-mode where all we are looking for are
                        # get block responses
                        with self.state_lock:
                            self.state = State.WAITING_FOR_CHAIN

                        peer_ip_addr = data["peer_ip_addr"]
                        peer_chain = self.get_chain_from_peer(peer_ip_addr, self.public_key_to_bytes())
                        if peer_chain != None and len(peer_chain) > len(self.blockchain.chain):
                            self.blockchain = peer_chain

                        with self.state_lock:
                            self.state = State.MINING
            else:
                print("rcv_buffer: got unsupported data type, ignoring")

            # To avoid throttling the CPU
            time.sleep(0.001)

    def get_port_from_peer_id(self, peer_pub_id):
        msg = ["GET-PEER", " ", str(len(peer_pub_id)), "\n"]
        msg_bytes = "".join(msg).encode() + peer_pub_id
        self.tracker_lock.acquire()

        self.tracker_socket.sendall(msg_bytes)
        header_bytes = self.tracker_socket_helper.get_data_until_newline()
        print(header_bytes)
        header = header_bytes.decode()

        if header != "PEER-PORT":
            print("Invalid header, expected PEER-PORT")
            self.tracker_lock.release()
            return None

        port = self.tracker_socket_helper.get_data_until_newline()

        self.tracker_lock.release()

        if int(port) == -1:
            return None

        return int(port)

    def get_chain_from_peer(self, peer_addr, peer_pub_id):
        curr_id = 0
        peer_chain = Blockchain()

        bad_chain = False

        listening_port = self.get_port_from_peer_id(peer_pub_id)

        while True:
            dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dest_socket.connect((peer_addr, listening_port))

            msg = ["GET-BLOCK", " ", str(curr_id), "\n"]
            msg_bytes = "".join(msg).encode()

            dest_socket.sendall(msg_bytes)

            dest_socket_helper = SocketHelper(dest_socket)
            header = dest_socket_helper.get_data_until_newline().decode()

            header_arr = header.split(' ')
            block_len = int(header_arr[1])

            block_encoded = dest_socket_helper.get_n_bytes_of_data(block_len)
            block_builder = Block()
            block = block_builder.from_bytes(block_encoded)

            if block.id == -1:
                print("get_chain_from_peer: Found end of chain.")
                dest_socket.close()
                break
            elif self.debug or block.is_valid(difficulty=4) and peer_chain.can_add_block_to_chain(block):
                print("get_chain_from_peer: Added block")
                peer_chain.add_block(block)
            else:
                print("get_chain_from_peer: found bad chain")
                bad_chain = True
                dest_socket.close()
                break

            dest_socket.close()

            curr_id += 1

        if bad_chain:
            return None

        return peer_chain

    def send_join_message(self):
        join_msg = "".join(["JOIN\n", str(self.listening_port), "\n"])
        self.tracker_socket.sendall(join_msg.encode())

        id_bytes = "".join(["ID", " ", str(len(self.public_key_to_bytes())), "\n"]).encode()
        id_bytes += self.public_key_to_bytes()
        self.tracker_socket.sendall(id_bytes)
        #TODO: Might want to wait for the peer to be registered
        with self.state_lock:
            self.state = State.MINING

    def request_nodes_from_tracker(self):
        peer_request = "LIST\n"
        self.tracker_lock.acquire()

        peer_bytes = "".join(["LIST", " ", str(len(self.public_key_to_bytes())), "\n"]).encode()
        peer_bytes += self.public_key_to_bytes()

        self.tracker_socket.sendall(peer_bytes)

        header_bytes = self.tracker_socket_helper.get_data_until_newline()
        header = header_bytes.decode()

        if header != "PEERS":
            print("Invalid header, expected PEERS")
            self.tracker_lock.release()
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
        all_bytes = header_bytes + block_bytes
        peer_socket.sendall(all_bytes)

    def broadcast_block_to_all_peers(self, block):
        print("broadcast_block_to_all_peers: broadcasting block")
        nodes_serialized = self.request_nodes_from_tracker()
        nodes = self.parse_serialized_nodes(nodes_serialized)

        self.send_lock.acquire()
        for node in nodes:
            curr_ip = socket.gethostbyname(socket.gethostname())
            # Don't broadcast node to yourself
            print(node[0])
            print(node[1])
            if node[0] == curr_ip and node[1] == self.listening_port:
                continue
            dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dest_socket.connect((node[0], node[1]))
            
            self.send_block_to_peer(block, "NEW", dest_socket)

            dest_socket.close()
        self.send_lock.release()
    
    def mine(self):
        """
        Mine for a block that contains a single transaction
        """
        print("Start mining")
        nonce = 0
        current_txn = None
        mine_id = 0

        while True:
            with self.state_lock:
                if self.state != State.MINING:
                    print("mine: skipped mining because state wasn't in mining mode")
                    continue
            with self.txn_lock:
                if len(self.txns) == 0 and not current_txn:
                    continue

                if not current_txn:
                    current_txn = self.txns.popleft()
                    current_txn.timestamp = time.time()
                    current_txn.sign(self.private_key)
            
            with self.blockchain_lock:
                latest_block = self.blockchain.get_latest_block()
                prev_hash = 0 if not latest_block else latest_block.hash
                mine_id = 0 if not latest_block else latest_block.id + 1
            
            timestamp = time.time()
            for _ in range(100):
                with self.blockchain_lock:
                    latest_block = self.blockchain.get_latest_block()
                    if latest_block and latest_block.id >= mine_id:
                        with self.txn_lock:
                            self.txns.appendleft(current_txn)
                        current_txn = None
                        nonce = 0
                        break
                
                nonce += 1
                new_block = Block.mine(mine_id, [current_txn], prev_hash, nonce, timestamp, self.difficulty)
                if new_block:
                    print("found a new block!")
                    with self.blockchain_lock:
                        latest_block = self.blockchain.get_latest_block()
                        if not latest_block or (latest_block.id+1 == mine_id):
                            print("mine: found valid block")
                            self.blockchain.add_block(new_block)
                            self.broadcast_block_to_all_peers(new_block)
                        else:
                            with self.txn_lock:
                                self.txns.appendleft(current_txn)
                    current_txn = None
                    nonce = 0
                    break
            time.sleep(0.1)

    def create_txn(self, data_dict):
        """
        Creates a transaction using the dictionary specified by data_dict

        Args:
            data_dict (dict): Some data that the user wants to send as part of a transaction
        """
        public_key_bytes = self.public_key_to_bytes()
        txn = Transaction(public_key_bytes, time.time(), data_dict)
        txn.sign(self.private_key)
        with self.txn_lock:
            self.txns.append(txn)

    def get_chain(self):
        with self.blockchain_lock:
            chain = self.blockchain.chain[:]
        return chain
# if __name__ == '__main__':
#     listening_port = int(sys.argv[1])
#     tracker_addr = sys.argv[2]
#     tracker_port = int(sys.argv[3])

#     difficulty = 4

#     if len(sys.argv) >= 5:
#         difficulty = int(sys.argv[4])
    
#     vote_file = None
#     if len(sys.argv) >= 6:
#         vote_file = sys.argv[5]

#     peer = Peer(tracker_addr, tracker_port, listening_port, difficulty, vote_file, debug=True)
#     peer.send_join_message()
    
    ################################################################ Get blockchain test
    # print(peer.get_port_from_peer_id(peer.public_key_to_bytes()))
    # dumb_chain = Blockchain()
    
    # transaction = Transaction(
    #     sender = peer.public_key_to_bytes(),
    #     timestamp= time.time(),
    #     data = "dummy"
    # )
    # transaction.sign(peer.private_key)

    # dummy_block = Block(_id=0, txns=[transaction], nonce=100, prev_hash=2, _hash=1)
    # dumb_chain.add_block(dummy_block)
    # peer.blockchain = dumb_chain 
    # dumb_network_chain = peer.get_chain_from_peer('127.0.0.1', peer.public_key_to_bytes())
    # print(dumb_network_chain.get_latest_block())
    # print(dumb_network_chain.get_latest_block().id)

    ############################################################################

    # serialized_nodes = peer.request_nodes_from_tracker()
    # nodes = peer.parse_serialized_nodes(serialized_nodes)
    # print(nodes)

    # dummy_block = Block(_id=1, data="dummy", nonce=100, prev_hash=2, _hash=1)
    # peer.broadcast_block_to_all_peers(dummy_block)
    # peer.request_block_from_all_peers(nodes, 100)