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

MAX_QUEUED_CONNECTIONS = 5

class Peer:
    def __init__(self, tracker_addr, tracker_port, listening_port, difficulty=4, vote_file=None):
        self.listening_port = listening_port
        self.tracker_addr = tracker_addr
        self.tracker_port = tracker_port
        self.tracker_lock = threading.Lock()

        self.send_lock = threading.Lock()

        self.rcv_buffer_lock = threading.Lock()
        self.rcv_buffer = deque()

        self.state_lock = threading.Lock()
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
        self.blockchain_lock = threading.Lock()

        self.votes = self.read_from_vote_file(vote_file)

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
                    votes.append(line)
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
                _id = int(header_arr[1])
                with self.blockchain_lock:
                    requested_block = self.blockchain.get_block_by_id(_id)
                    
                    # If our chain is empty, create a fake block
                    if not requested_block:
                        fake_txn = Transaction(b"", time.time(), "")
                        fake_txn.sign(self.private_key)
                        requested_block = Block(0, [fake_txn], 0, 0, 0, time.time())

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

                    if not latest_block: # This peer does not have any blocks in its chain
                        print(f"added block {block.id} to chain")
                        self.blockchain.add_block(block)
                    elif latest_block.id < _id: # This is non-forking case when received block comes after current last block in our chain
                        if latest_block.hash != block.prev_hash:
                            continue
                        print(f"added block {block.id} to chain")
                        self.blockchain.add_block(block)
                    elif latest_block.id >= _id:
                        print("Forking")
                        block_at_fork = self.blockchain.get_block_by_id(_id)
                        if str(block_at_fork) == str(block): # We already have this block, just ignore it
                            continue

                        # Forking logic :)
                        # Set state to wait-mode where all we are looking for are
                        # get block responses
                        with self.state_lock:
                            self.state = State.WAITING_FOR_CHAIN
                        
                        # Send get block requests to all the peer nodes
                        peer_nodes_serialized = self.request_nodes_from_tracker()
                        peer_nodes = self.parse_serialized_nodes(peer_nodes_serialized)
                        peer_blocks = self.request_block_from_all_peers(peer_nodes, _id)

                        # Track the number of votes for each block variation via their hashes (basically a hash table)
                        hash_counts = {}
                        for peer_block in peer_blocks:
                            hash_counts.setdefault(peer_block.hash, 0)
                            hash_counts[peer_block.hash] += 1
                        
                        max_count = max(hash_counts.values())

                        max_hashes = [key for key, value in hash_counts.items() if value == max_count]
                        max_hash = max_hashes[0]
                        new_block = [blk for blk in peer_blocks if blk.hash == max_hash][0]

                        # handle multiple majority votes
                        if len(max_hashes) > 1:
                            max_blocks = [blk for blk in peer_blocks if blk.hash in max_hashes]
                            for blk in max_blocks:
                                if blk.timestamp < new_block.timestamp:
                                    new_block = blk

                        # Swap blocks if needed
                        if block_at_fork.hash != new_block.hash:
                            # Get the transactions that were lost after swap
                            dropped_transactions = self.blockchain.swap_block(new_block, self.public_key_to_bytes())
                            dropped_votes = [txn.data for txn in dropped_transactions]
                            self.votes.extend(dropped_votes)
                        
                        with self.state_lock:
                            self.state = State.MINING

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
        with self.state_lock:
            self.state = State.MINING

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
    
    def mine(self):
        """
        Mine for a block that contains a single transaction
        """
        print("Start mining")
        nonce = 0
        current_txn = None

        while True:
            with self.state_lock:
                if self.state != State.MINING:
                    continue

            if not self.votes and not current_txn:
                continue

            if not current_txn:
                data = self.votes.pop()
                public_key_bytes = self.public_key_to_bytes()
                txn = Transaction(public_key_bytes, time.time(), data)
                txn.sign(self.private_key)
                current_txn = txn
            
            with self.blockchain_lock:
                latest_block = self.blockchain.get_latest_block()
                prev_hash = 0 if not latest_block else latest_block.hash
                mine_id = 0 if not latest_block else latest_block.id + 1
            
            timestamp = time.time()
            for _ in range(100):
                nonce += 1
                new_block = Block.mine(mine_id, [txn], prev_hash, nonce, timestamp, self.difficulty)
                if new_block:
                    with self.blockchain_lock:
                        latest_block = self.blockchain.get_latest_block()
                        if not latest_block or (latest_block.id == mine_id + 1):
                            self.blockchain.add_block(new_block)
                        else:
                            break
                    self.broadcast_block_to_all_peers(new_block)
                    current_txn = None
                    nonce = 0
                    break
            time.sleep(0.1)            

if __name__ == '__main__':
    listening_port = int(sys.argv[1])
    tracker_addr = sys.argv[2]
    tracker_port = int(sys.argv[3])

    difficulty = 4

    if len(sys.argv) <= 5:
        difficulty = int(sys.argv[4])
    
    vote_file = None
    if len(sys.argv) <= 6:
        vote_file = sys.argv[5]

    peer = Peer(tracker_addr, tracker_port, listening_port, difficulty, vote_file)
    peer.send_join_message()

    # serialized_nodes = peer.request_nodes_from_tracker()
    # nodes = peer.parse_serialized_nodes(serialized_nodes)
    # print(nodes)

    # dummy_block = Block(_id=1, data="dummy", nonce=100, prev_hash=2, _hash=1)
    # peer.broadcast_block_to_all_peers(dummy_block)
    # peer.request_block_from_all_peers(nodes, 100)


