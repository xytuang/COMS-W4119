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
        """
        The Peer is responsible for the core blockchain logic -- mining, adding new blocks to the chain,
        handling forking, etc. Upon intitialization, it starts a few different threads: a mining thread,
        a thread to listen for new connections and serve/receive blocks, and a thread to process received
        blocks.

        Args:
            tracker_addr (str): ip address of the tracker
            tracker_port (int): the tracker port
            listening_port (int): this peer's port to listen for requests from
            difficulty (int): how many 0's the hash needs to start with to be consider valid
            debug (boolean): debug flag that allows some checks to be bypassed for unit-testing
        """
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

        self.polling_thread = threading.Thread(target=self.poll_from_rcv_buffer)

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
        
        self.tamper_freq = None
        self.tamper_type = None
        self.broadcast_freq = None
        self.curr_step = 0


    def set_configs_from_file(self, config_file):
        """
        Reads configs from a file and sets them internally, used only for testing.

        Args:
            config_file (str): name of the configuration json file
        """
        config_data = None
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            if "tamper_freq" in config_data:
                self.tamper_freq = config_data["tamper_freq"]
                # print("LOG set_configs_from_file: Block tamper frequency (for testing resiliency to bad data):", str(self.tamper_freq), file=self.log_file)
            if "broadcast_freq" in config_data:
                self.broadcast_freq = config_data["broadcast_freq"]
                # print("LOG set_configs_from_file: Block broadcast frequency (for testing forks):", str(self.broadcast_freq), file=self.log_file)
            if "tamper_type" in config_data:
                self.tamper_type = config_data["tamper_type"]

    def public_key_to_bytes(self):
        """
        Converts the peer's public key into bytes

        Returns:
            bytes: the serialized public key
        """
        public_key_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_key_bytes

    def process_peer_connections(self, listening_sock):
        """
        Listens for peer connections and serves any requests. In particular,
        puts blocks sent by other peers on a rcv buffer that another thread pulls
        from to try and add blocks to the chain. Also serves requests for a particular block
        on the chain.

        Args:
            listening_sock (socket): "server"-side socket for other peers to connect to
        """

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
                elif header_arr[0] == "GET-CHAIN":
                    with self.blockchain_lock:
                        for _id in range(len(self.blockchain.chain)):
                            exist_block = self.blockchain.get_block_by_id(_id)
                            self.send_block_to_peer(exist_block, "EXIST", peer_socket)

                        fake_txn = Transaction(b"", time.time(), {})
                        fake_txn.sign(self.private_key)
                        end_block = Block(-1, [fake_txn], 0, 0, 0, time.time())

                        self.send_block_to_peer(end_block, "EXIST", peer_socket)

                        print("LOG process_peer_connections: finished sending chain of length", len(self.blockchain.chain), file=self.log_file)
                else:
                    print("LOG process_peer_connections: Unsupported header type", file=self.log_file)
                
            except socket.timeout:
                # if just a timeout, continue and check check shutdown flag
                continue
            except Exception as e:
                print(f"LOG process_peer_connections: Error in process_peer_connections (may be expected if closing): {e}", file=self.log_file)
            finally:
                try:
                    peer_socket.close()
                except:
                    pass
        print("LOG process_peer_connections: Listening thread terminated", file=self.log_file)
        
    def poll_from_rcv_buffer(self):
        """
        Continuously listens for received blocks off the rcv buffer and tries to add them to the node's current chain.
        It is also responsible for detecting possible forking scenarios and replacing the node's chain with the peer's
        if it is valid and longer.
        """
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
                print(f"LOG poll_from_rcv_buffer: received block (id={data['payload'].id}) data: ", data, file=self.log_file)

                block = data["payload"]
                _id = block.id

                if not block.is_valid(self.difficulty):
                    print("LOG poll_from_rcv_buffer: received invalid block, discarding", file=self.log_file)
                    continue

                with self.blockchain_lock:
                    latest_block = self.blockchain.get_latest_block()

                    # Hash matches and the block ID is the next expected one
                    if self.blockchain.can_add_block_to_chain(block):
                        print(f"LOG poll_from_rcv_buffer: adding block {block.id} to chain", file=self.log_file)
                        self.blockchain.add_block(block)
                        chain = [f"id: {blk.id}" for blk in self.blockchain.chain]
                        print(f"LOG poll_from_rcv_buffer: added block, current state of blockchain: {chain}", file=self.log_file)
                    
                    # If the incoming block is valid and has more work done, potential fork
                    elif _id >= len(self.blockchain.chain):
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

                        # peer's chain is longer, so we switch to it
                        if peer_chain != None and len(peer_chain.chain) > len(self.blockchain.chain): 
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

    def get_port_from_peer_id(self, peer_pub_id):
        """
        Retrieves the port of a peer from the tracker

        Args:
            peer_pub_id (bytes): the public ID of the peer
        Returns:
            int: listening port of the peer
        """
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
        """
        Retrieves the chain from a peer given a peer's IP address and public ID.
        It uses the peer's public ID to get the peer's listening port from the tracker
        so it knows where to connect to.

        Args:
            peer_addr (string): IP address of the peer
            peer_pub_id (bytes): public ID of the peer
        Returns:
            Blockchain: the peer's blockchain
        """
        curr_id = 0
        peer_chain = Blockchain()

        bad_chain = False

        listening_port = self.get_port_from_peer_id(peer_pub_id)

        dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dest_socket.connect((peer_addr, listening_port))
        print("LOG get_chain_from_peer: Connected to peer.", file=self.log_file)

        msg = ["GET-CHAIN", "\n"]
        msg_bytes = "".join(msg).encode()

        print("LOG get_chain_from_peer: Requesting block ID", str(curr_id), file=self.log_file)

        dest_socket.sendall(msg_bytes)

        dest_socket_helper = SocketHelper(dest_socket)

        while True:
            header = dest_socket_helper.get_data_until_newline().decode()

            if header == None:
                bad_chain = True
                break

            header_arr = header.split(' ')
            block_len = int(header_arr[1])

            block_encoded = dest_socket_helper.get_n_bytes_of_data(block_len)
            block_builder = Block()
            block = block_builder.from_bytes(block_encoded)

            if block.id == -1:
                print("LOG get_chain_from_peer: Found end of chain.", file=self.log_file)
                break
            elif self.debug or (block.is_valid(difficulty=self.difficulty) and peer_chain.can_add_block_to_chain(block)):
                print("LOG get_chain_from_peer: Added block to candidate chain", file=self.log_file)
                peer_chain.add_block(block)
            else:
                print("LOG get_chain_from_peer: Found bad chain", file=self.log_file)
                bad_chain = True
                break

        if not bad_chain:
            print("LOG get_chain_from_peer: Got chain with length", len(peer_chain.chain), file=self.log_file)

        dest_socket.close()

        if bad_chain:
            return None

        return peer_chain

    def send_join_message(self):
        """
        Handles the joining logic when a peer becomes a part of the network.

        It registers with the tracker by sending a JOIN message with its listening port
        for other peers to connect to, as well as an ID message with the node's public key
        to allow the tracker to uniquely identify the peer. Finally, it requests a list of peers
        and asks each of the peer for their respective chains so it can select the longest one as
        its own.

        After registration, it allows mining to start.
        """
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

            # Request chain from peer
            dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dest_socket.connect((node[0], node[1]))
            print("LOG send_join_message: Connected to peer.", file=self.log_file)

            msg = ["GET-CHAIN", "\n"]
            msg_bytes = "".join(msg).encode()

            print("LOG send_join_message: Requesting chain", file=self.log_file)

            dest_socket.sendall(msg_bytes)

            dest_socket_helper = SocketHelper(dest_socket)
            while True:
                header = dest_socket_helper.get_data_until_newline().decode()

                header_arr = header.split(' ')
                block_len = int(header_arr[1])

                block_encoded = dest_socket_helper.get_n_bytes_of_data(block_len)
                block_builder = Block()
                block = block_builder.from_bytes(block_encoded)

                if block.id == -1:
                    print("LOG send_join_message: Found end of chain.", file=self.log_file)
                    break

                elif self.debug or (block.is_valid(difficulty=self.difficulty) and peer_chain.can_add_block_to_chain(block)):
                    print("LOG send_join_message: Added block to candidate chain", file=self.log_file)
                    peer_chain.add_block(block)
                else:
                    print("LOG send_join_message: Found bad chain", file=self.log_file)
                    bad_chain = True
                    break

            dest_socket.close()

            if not bad_chain and len(peer_chain.chain) > len(best_chain.chain):
                best_chain = peer_chain

        with self.blockchain_lock:
            self.blockchain = best_chain

        self.polling_thread.start()
        self.listening_thread.start()
        self.mining_thread.start()

        with self.state_lock:
            self.state = State.MINING

    def request_nodes_from_tracker(self):
        """
        Gets a list of all the nodes from the tracker in serialized form

        Returns:
            str: string representing the nodes from the tracker
        """
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
        """
        Helper function to parse serialized nodes retrieved from the tracker

        Args:
            node_str: the string representing serialized nodes
        Returns:
            tuple[]: array of tuples with format (Peer IP Address, Peer listening port)
        """
        if len(node_str) == 0:
            return []

        nodes = node_str.split(' ')
        # Array of tuples with format (IP Address, listening port)
        node_arr = []
        for node in nodes:
            pair = node.split(',')
            node_arr.append( (pair[0], int(pair[1])) )
        return node_arr

    def send_block_to_peer(self, block, tag, peer_socket):
        """
        Sends a block to a peer

        Args:
            block (Block): the block to be sent
            tag (string): the type of block being sent (e.g. existing or new)
            peer_socket (socket): the socket for the connection to othe ther peer
        """
        block_bytes = block.to_bytes()
        block_msg_header = ["BLOCK", " ", str(len(block_bytes)), " ", tag, "\n"]
        header_bytes = "".join(block_msg_header).encode()
        all_bytes = header_bytes + block_bytes
        peer_socket.sendall(all_bytes)

    def broadcast_block_to_all_peers(self, block):
        """
        Broadcasts a block to all of the node's peers

        Args:
            Block: the block to be broadcast
        """
        print(f"LOG broadcast_block_to_all_peers: broadcasting block {block.id}", file=self.log_file)
        
        # don't broadcast during shutdown
        if self.shutdown_event.is_set():
            return

        # Get list of nodes to broadcast to
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
        Persistently mine for a block that contains a single transaction. Constantly
        sniffs for a transaction to mine off a queue of pending transactions.
        """
        nonce = 0
        current_txn = None
        mine_id = 0

        while not self.shutdown_event.is_set():
            time.sleep(0.001)
            with self.state_lock:
                if self.state != State.MINING:
                    continue

            with self.txn_lock:
                # No transactions to mine
                if len(self.txns) == 0 and not current_txn:
                    continue

                # If no transaction is currently being mined,
                # see if there's anything on the transaction queue
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

                # If we discover that someone else already mined the block with our target id,
                # then restart the mining process by adding it back to the first spot of the
                # transaction mining queue
                with self.blockchain_lock:
                    latest_block = self.blockchain.get_latest_block()
                    if latest_block and latest_block.id >= mine_id:
                        with self.txn_lock:
                            self.txns.appendleft(current_txn)
                        current_txn = None
                        nonce = 0
                        break

                new_block = Block.mine(mine_id, [current_txn], prev_hash, nonce, timestamp, self.difficulty)
                nonce += 1
                if new_block:
                    print(f"LOG mine: found a new block {new_block.id}", file=self.log_file)
                    with self.blockchain_lock:
                        if self.blockchain.is_new_block_repeat_poll(new_block):
                            print("LOG mine: rejecting poll creation block due to poll already existing in the chain", file=self.log_file)
                        elif self.blockchain.is_new_block_vote_for_nonexistent_poll(new_block):
                            print("LOG mine: rejecting vote due to poll not existing on the chain")
                        else:
                            latest_block = self.blockchain.get_latest_block()
                            if not latest_block or (latest_block.id+1 == mine_id):
                                print("LOG mine: found valid block, adding to chain", file=self.log_file)
                                self.blockchain.add_block(new_block)

                                # Broadcast frequency determines how often a block is broadcast. For testing only
                                if self.broadcast_freq == None or self.curr_step % self.broadcast_freq == 0:
                                    print("LOG mine: broadcasting block to all peers", file=self.log_file)

                                    # Tamper with the outgoing block, for testing modified block scenarios (and is only for testing)
                                    tampered = False
                                    if self.tamper_freq != None and self.curr_step % self.tamper_freq == 0:
                                        tampered = True
                                        print("LOG mine: tampering with block (for testing)", file=self.log_file)
                                        print("LOG mine: tamper type:", self.tamper_type, file=self.log_file)
                                        tmp = None
                                        if self.tamper_type == None or self.tamper_type == "hash":
                                            tmp = new_block.hash
                                            new_block.hash = 12345
                                        elif self.tamper_type == "prev_hash":
                                            tmp = new_block.prev_hash
                                            new_block.prev_hash = 23456
                                        elif self.tamper_type == "txn_data":
                                            tmp = new_block.txns[0].data["poll_id"]
                                            new_block.txns[0].data["poll_id"] = "ID_THAT_YOU_WILL_REALLY_IMPROBABILISTICALLY_ENTER_ON_ACCIDENT"
                                        elif self.tamper_type == "chain":
                                            if len(self.blockchain.chain) < 2:
                                                print("LOG mine: skipping tampering with chain due to chain being too small", file=self.log_file)
                                            else:
                                                self.blockchain.chain[1].hash = 38294329432
                                        else:
                                            tmp = new_block.hash
                                            print("LOG mine: unsupported tamper type, defaulting to hash", file=self.log_file)
                                            new_block.hash = 12345

                                    # Broadcast the newly mined block to all peers
                                    self.broadcast_block_to_all_peers(new_block)

                                    # Restore data so the underlying chain still remains consistent, as tampering here is intended for corrupting
                                    # data in transit unless it's a chain type tamper, which will permanently invalidate a block on the chain.
                                    if tampered:
                                        if self.tamper_type == None or self.tamper_type == "hash":
                                            new_block.hash = tmp
                                        elif self.tamper_type == "prev_hash":
                                            new_block.prev_hash = tmp
                                        elif self.tamper_type == "txn_data":
                                            new_block.txns[0].data["poll_id"] = tmp
                                        elif self.tamper_type == "chain":
                                            # Don't restore chain data because it's meant to be permanent
                                            pass
                                        else:
                                            new_block.hash = tmp

                                if self.broadcast_freq != None or self.tamper_freq != None:
                                    self.curr_step += 1

                                chain_str = [f"id: {blk.id}" for blk in self.blockchain.chain]
                                print(f"LOG mine: current state of blockchain: {chain_str}", file=self.log_file)
                            else:
                                with self.txn_lock:
                                    self.txns.appendleft(current_txn)
                    current_txn = None
                    nonce = 0
                    break

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
        """
        Retrieves the underlying blockchain of the peer

        Returns:
            Block[]: a list of blocks in the order they were placed onto the blockchain
        """
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
