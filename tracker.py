
import socket
import threading
import sys
from socket_helper import SocketHelper

MAX_QUEUED_CONNECTIONS = 5

active_peers = {}
active_peers_lock = threading.Lock()

# Usage: python3 tracker.py <tracker_port>

def delete_peer(peer_id):
    active_peers_lock.acquire()
    del active_peers[peer_id]
    active_peers_lock.release()

def serialize_active_peers(curr_peer_addr):
    active_peers_lock.acquire()

    res = ['PEERS', '\n']

    exist_active_peers = False
    for peer_addr in active_peers:
        # Skip the peer you're sending to
        if peer_addr == curr_peer_addr:
            continue
        peer = active_peers[peer_addr]
        exist_active_peers = True
        res.append(peer.addr[0]) # IP address
        res.append(',')
        res.append(peer.listening_port)
        res.append(' ')

    if exist_active_peers:
        res[-1] = '\n'
    else:
        res.append('\n')

    active_peers_lock.release()

    print(res)

    return "".join(res)

def process_peer_requests(peer):
    print("Connected to peer at:", peer.addr[0])
    peer_socket_helper = SocketHelper(peer.socket)
    # Listen for the join message
    join_header_bytes = peer_socket_helper.get_data_until_newline()

    # If the node disconnects or breaks protocol, terminate the thread immediately
    if join_header_bytes == None or join_header_bytes.decode() != "JOIN":
        return

    # Used to tell other peers which port to connect to
    peer_listening_port = peer_socket_helper.get_data_until_newline().decode()
    peer.listening_port = peer_listening_port

    print("Peer listening port:",peer.listening_port)

    pub_id_header_bytes = peer_socket_helper.get_data_until_newline()

    if pub_id_header_bytes == None:
        return

    pub_id_header = pub_id_header_bytes.decode().split(' ')
    if pub_id_header[0] != "ID":
        return

    pub_key_len = int(pub_id_header[1])

    peer.pub_id = peer_socket_helper.get_n_bytes_of_data(pub_key_len)

    # Once we recieve the peer ID, add it to the list
    active_peers_lock.acquire()
    active_peers[peer.pub_id] = peer
    active_peers_lock.release()
    
    print("Peer ID (bytes):",peer.pub_id)

    #TODO: Might want to send ACK that the peer has been registered

    # Listen for request to send list of peers
    while True:
        header_bytes = peer_socket_helper.get_data_until_newline()
        if header_bytes == None:
            break

        header = header_bytes.decode()
        if header == "LIST":
            active_peers_str = serialize_active_peers(peer.addr)

            print("Sending peers:", active_peers_str)

            active_peers_bytes = active_peers_str.encode()

            # Send list of peers
            peer.socket.sendall(active_peers_bytes)
        else:
            header_arr = header.split(' ')
            if header_arr[0] != "GET-PEER":
                break

            print("Serving GET-PEER request")

            pub_id_len = int(header_arr[1])

            peer_pub_id = peer_socket_helper.get_n_bytes_of_data(pub_id_len)
            msg = ["PEER-PORT", "\n"]
            active_peers_lock.acquire()
            if peer_pub_id in active_peers:
                msg.append(str(active_peers[peer_pub_id].listening_port))
                msg.append("\n")
            else:
                msg.append("-1")
                msg.append("\n")
            active_peers_lock.release()
            peer.socket.sendall("".join(msg).encode())
            print("Sending ", "".join(msg))

    # If connection closed, remove peer from list
    peer.socket.close()
    delete_peer(peer.pub_id)

    print("Disconnected peer at " + str(peer.addr))
    
class PeerConn:
    def __init__(self):
        self.socket = None
        self.addr = None
        self.listening_port = None
        self.pub_id = None

class Tracker:
    def __init__(self, tracker_port):
        self.threads = []
        self.threads_list_lock = threading.Lock()
        self.tracker_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_sock.bind(('', tracker_port))

    def listen_for_connections(self):
        print("Started main listening thread.")
        self.tracker_sock.listen(MAX_QUEUED_CONNECTIONS)
        while True:
            peer_socket, addr = self.tracker_sock.accept()

            peer = PeerConn()
            peer.addr = addr
            peer.socket = peer_socket

            peer_conn_thread = threading.Thread(target=process_peer_requests, args=(peer,))
            peer_conn_thread.start()

if __name__ == '__main__':
    tracker_port = sys.argv[1]
    tracker = Tracker(int(tracker_port))
    tracker.listen_for_connections()    