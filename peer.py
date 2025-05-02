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
    def __init__(self, tracker_addr, tracker_port, listening_port, difficulty=4, debug=False):
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

        self.log_file = open(f"{self.listening_port}_log.txt", "w")

        self.shutdown_event = threading.Event()

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
        
        self.tamper_freq = None
        self.broadcast_freq = None
        self.curr_step = 0


    def set_configs_from_file(self, config_file):
        # print("LOG set_configs_from_file: setting configurations...", file=self.log_file)
        config_data = None
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            if "tamper_freq" in config_data:
                self.tamper_freq = config_data["tamper_freq"]
                # print("LOG set_configs_from_file: Block tamper frequency (for testing resiliency to bad data):", str(self.tamper_freq), file=self.log_file)
            if "broadcast_freq" in config_data:
                self.broadcast_freq = config_data["broadcast_freq"]
                # print("LOG set_configs_from_file: Block broadcast frequency (for testing forks):", str(self.broadcast_freq), file=self.log_file)

    def public_key_to_bytes(self):
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_key_bytes

    def process_peer_connections(self, listening_sock):
        # print("LOG process_peer_connections: Started listening thread.", file=self.log_file)
        listening_sock.listen(MAX_QUEUED_CONNECTIONS)
        # set a timeout so we can check for shutdown periodically
        listening_sock.settimeout(1.0)
        
        while not self.shutdown_event.is_set():            
            try:
                peer_socket, addr = listening_sock.accept()
                peer_socket_helper = SocketHelper(peer_socket)
                print("LOG process_peer_connections: Connected to new peer.", file=self.log_file)
                header = peer_socket_helper.get_data_until_newline().decode()
                header_arr = header.split(' ')
                print("LOG process_peer_connections: found header", header_arr, file=self.log_file)
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
                    print("LOG process_peer_connections: Unsupported header type", file=self.log_file)

                peer_socket.close()
            except socket.timeout:
                # if just a timeout, continue and check check shutdown flag
                continue
            except Exception as e:
                print(f"LOG process_peer_connections: Error in process_peer_connections (may be expected if closing): {e}", file=self.log_file)
        print("LOG process_peer_connections: Listening thread terminated", file=self.log_file)
        
    def poll_from_rcv_buffer(self):
        while not self.shutdown_event.is_set():
            # To avoid throttling the CPU
            time.sleep(0.001)

            data = None
            self.rcv_buffer_lock.acquire()
            if len(self.rcv_buffer) > 0:
                data = self.rcv_buffer.popleft()

            self.rcv_buffer_lock.release()

            if data == None:
                continue

            if data["type"] == "BLOCK":
                print("LOG poll_from_rcv_buffer: received block data: ", data, file=self.log_file)

                block = data["payload"]
                _id = block.id

                if not block.is_valid(self.difficulty):
                    print("LOG poll_from_rcv_buffer: received invalid block, discarding", file=self.log_file)
                    continue

                with self.blockchain_lock:
                    latest_block = self.blockchain.get_latest_block()

                    # Hash matches and the block ID is the next expected one
                    if self.blockchain.can_add_block_to_chain(block):
                        print(f"LOG poll_from_rcv_buffer: added block {block.id} to chain", file=self.log_file)
                        self.blockchain.add_block(block)
                        chain = [f"id: {blk.id}" for blk in self.blockchain.chain]
                        print(f"LOG poll_from_rcv_buffer: current state of blockchain: {chain}", file=self.log_file)
                    
                    # If the incoming block is valid and has more work done, potential fork
                    elif _id > len(self.blockchain.chain):
                        print(f"LOG poll_from_rcv_buffer: Detected fork (new id: {str(_id)}, chain len: {len(self.blockchain.chain)}), resolving", file=self.log_file)
                        # Forking logic :)
                        # Set state to wait-mode where all we are looking for are
                        # get block responses
                        with self.state_lock:
                            # avoid state changes during shutdown (same below)
                            if self.shutdown_event.is_set():
                                break
                            self.state = State.WAITING_FOR_CHAIN

                        peer_ip_addr = data["peer_ip_addr"]
                        peer_chain = self.get_chain_from_peer(peer_ip_addr, block.txns[0].sender)

                        if peer_chain != None and len(peer_chain.chain) > len(self.blockchain.chain): # peer's chain is longer, we switch to it
                            # Update logic to find fork point and remine transactions in lost blocks
                            # idx is set to the fork point after the while loop
                            idx = 0
                            while (idx < len(self.blockchain.chain)):
                                peer_block_hash = peer_chain.chain[idx].hash
                                own_block_hash = self.blockchain.chain[idx].hash
                                if peer_block_hash == own_block_hash:
                                    idx += 1
                                    continue
                                else:
                                    break
                            
                            # grab all the lost transactions in the shorter chain
                            lost_txns = []
                            public_key_bytes = self.public_key_to_bytes()
                            chain_len = len(self.blockchain.chain)

                            for i in range(idx, chain_len):
                                blk = self.blockchain.chain[i]
                                for txn in blk.txns:
                                    if txn.sender == public_key_bytes:
                                        lost_txns.append(txn)
                            # We need to traverse lost_txns in reverse order
                            # Newer txns are at the back of lost_txns
                            # We are using appendleft to append to the front of self.txns
                            # Without reversing, we would appending newer transactions to the front of self.txns
                            with self.txn_lock:
                                for txn in reversed(lost_txns):
                                    self.txns.appendleft(txn)

                            self.blockchain = peer_chain
                        with self.state_lock:
                            if self.shutdown_event.is_set():
                                break
                            self.state = State.MINING
                        
                        chain = [f"id: {blk.id}" for blk in self.blockchain.chain]
                        print(f"LOG poll_from_rcv_buffer: current state of blockchain: {chain}", file=self.log_file)
                    else:
                        print("LOG poll_from_rcv_buffer: Could not add block to chain and did not detect a fork, discarding", file=self.log_file)
            else:
                print("LOG poll_from_rcv_buffer: got unsupported data type, ignoring", file=self.log_file)
        # print("LOG poll_from_rcv_buffer: Polling thread terminated", file=self.log_file)

    def get_port_from_peer_id(self, peer_pub_id):
        msg = ["GET-PEER", " ", str(len(peer_pub_id)), "\n"]
        msg_bytes = "".join(msg).encode() + peer_pub_id
        self.tracker_lock.acquire()

        self.tracker_socket.sendall(msg_bytes)
        header_bytes = self.tracker_socket_helper.get_data_until_newline()
        header = header_bytes.decode()

        if header != "PEER-PORT":
            print("LOG get_port_from_peer_id: Invalid header, expected PEER-PORT", file=self.log_file)
            self.tracker_lock.release()
            return None

        port = self.tracker_socket_helper.get_data_until_newline()
        print("LOG get_port_from_peer_id: got port", port, file=self.log_file)

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
            print("LOG get_chain_from_peer: Connected to peer.", file=self.log_file)

            msg = ["GET-BLOCK", " ", str(curr_id), "\n"]
            msg_bytes = "".join(msg).encode()

            print("LOG get_chain_from_peer: Requesting block ID", str(curr_id), file=self.log_file)

            dest_socket.sendall(msg_bytes)

            dest_socket_helper = SocketHelper(dest_socket)
            header = dest_socket_helper.get_data_until_newline().decode()

            header_arr = header.split(' ')
            block_len = int(header_arr[1])

            block_encoded = dest_socket_helper.get_n_bytes_of_data(block_len)
            block_builder = Block()
            block = block_builder.from_bytes(block_encoded)

            if block.id == -1:
                print("LOG get_chain_from_peer: Found end of chain.", file=self.log_file)
                dest_socket.close()
                break
            elif self.debug or (block.is_valid(difficulty=self.difficulty) and peer_chain.can_add_block_to_chain(block)):
                print("LOG get_chain_from_peer: Added block", file=self.log_file)
                peer_chain.add_block(block)
            else:
                print("LOG get_chain_from_peer: found bad chain", file=self.log_file)
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

        # pick up the active peer list and get chain from all peers
        header_bytes = self.tracker_socket_helper.get_data_until_newline()
        header = header_bytes.decode()

        if header != "PEERS":
            print("Invalid header, expected PEERS")
            return None

        nodes_bytes = self.tracker_socket_helper.get_data_until_newline()
        nodes_serialized = nodes_bytes.decode()
        nodes = self.parse_serialized_nodes(nodes_serialized)


        # set our chain to the longest chain currently present in the network
        best_chain = Blockchain()

        for node in nodes:
            curr_id = 0
            peer_chain = Blockchain()
            bad_chain = False

            while True:
                dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                dest_socket.connect((node[0], node[1]))
                # print("LOG get_chain_from_peer: Connected to peer.", file=self.log_file)

                msg = ["GET-BLOCK", " ", str(curr_id), "\n"]
                msg_bytes = "".join(msg).encode()

                # print("LOG get_chain_from_peer: Requesting block ID", str(curr_id), file=self.log_file)

                dest_socket.sendall(msg_bytes)

                dest_socket_helper = SocketHelper(dest_socket)
                header = dest_socket_helper.get_data_until_newline().decode()

                header_arr = header.split(' ')
                block_len = int(header_arr[1])

                block_encoded = dest_socket_helper.get_n_bytes_of_data(block_len)
                block_builder = Block()
                block = block_builder.from_bytes(block_encoded)

                if block.id == -1:
                    # print("LOG get_chain_from_peer: Found end of chain.", file=self.log_file)
                    dest_socket.close()
                    break

                elif self.debug or (block.is_valid(difficulty=self.difficulty) and peer_chain.can_add_block_to_chain(block)):
                    # print("LOG get_chain_from_peer: Added block", file=self.log_file)
                    peer_chain.add_block(block)
                else:
                    # print("LOG get_chain_from_peer: found bad chain", file=self.log_file)
                    bad_chain = True
                    dest_socket.close()
                    break

                dest_socket.close()

                curr_id += 1

            if not bad_chain and len(peer_chain.chain) > len(best_chain.chain):
                best_chain = peer_chain
        
        self.blockchain = best_chain

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
        print(f"LOG broadcast_block_to_all_peers: broadcasting block {block.id}", file=self.log_file)
        
        # dont broadcast during shutdown
        if self.shutdown_event.is_set():
            return

        nodes_serialized = self.request_nodes_from_tracker()
        nodes = self.parse_serialized_nodes(nodes_serialized)

        self.send_lock.acquire()

        try:
            for node in nodes:
                try:
                    dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    dest_socket.connect((node[0], node[1]))
                    
                    self.send_block_to_peer(block, "NEW", dest_socket)

                    dest_socket.close()
                except Exception as e:
                    print(f"Error connecting to peer at {node[0]}:{node[1]}: {e}")
                    try:
                        dest_socket.close() # still gotta trying closing it
                    except:
                        pass
        except Exception as e:
            print(f"Error during broadcast: {e}")
        finally:
            self.send_lock.release()
    
    def mine(self):
        """
        Mine for a block that contains a single transaction
        """
        # print("LOG mine: Start mining thread", file=self.log_file)
        nonce = 0
        current_txn = None
        mine_id = 0

        while not self.shutdown_event.is_set():
            time.sleep(0.001)
            with self.state_lock:
                if self.state != State.MINING:
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
                if self.shutdown_event.is_set():
                    break
                
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
                    print(f"LOG mine: found a new block {new_block.id}", file=self.log_file)
                    with self.blockchain_lock:
                        if self.blockchain.is_new_block_repeat_poll(new_block):
                            print("LOG mine: rejecting poll creation block due to poll already existing in the chain", file=self.log_file)
                        else:
                            latest_block = self.blockchain.get_latest_block()
                            if not latest_block or (latest_block.id+1 == mine_id):
                                print("LOG mine: found valid block, adding to chain", file=self.log_file)
                                self.blockchain.add_block(new_block)
                                if self.broadcast_freq == None or self.curr_step % self.broadcast_freq == 0:
                                    # print("LOG mine: broadcasting block to all peers", file=self.log_file)
                                    if self.tamper_freq != None and self.curr_step % self.tamper_freq == 0:
                                        print("LOG mine: tampering with block hash (for testing)", file=self.log_file)
                                        new_block.hash = 12345
                                    self.broadcast_block_to_all_peers(new_block)
                                if self.broadcast_freq != None or self.tamper_freq != None:
                                    self.curr_step += 1
                                chain = [f"id: {blk.id}" for blk in self.blockchain.chain]
                                print(f"LOG mine: current state of blockchain: {chain}", file=self.log_file)
                            else:
                                with self.txn_lock:
                                    self.txns.appendleft(current_txn)
                    current_txn = None
                    nonce = 0
                    break
            
        # print("LOG mine: Mining thread terminated", file=self.log_file)

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
            print(f"LOG create_txn: submitted mining job {data_dict}", file=self.log_file)
            self.txns.append(txn)

    def get_chain(self):
        with self.blockchain_lock:
            chain = self.blockchain.chain[:]
        return chain

    def send_leave_message(self):
        """
        Notifies the tracker that this peer is leaving the network
        """
        try:
            with self.tracker_lock:
                leave_msg = "LEAVE\n"
                self.tracker_socket.sendall(leave_msg.encode())
                print("Sent LEAVE msg to tracker")
        except Exception as e:
            print(f"Error sending LEAVE message: {e}")
    
    
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