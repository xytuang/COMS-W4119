
import socket
import threading
import sys
import time
from socket_helper import SocketHelper

# Usage: python3 tracker_tester.py <tracker IP address> <tracker port>

# Not used for now, it's for the peer to listen for connections from other peers
LISTENING_PORT = 50000

if __name__ == '__main__':
    tracker_addr = sys.argv[1]
    tracker_port = int(sys.argv[2])

    #
    # In the actual peer, would probably want to bind the listening socket here
    #

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((tracker_addr, tracker_port))

    client_socket_helper = SocketHelper(client_socket)

    join_msg = "".join(["JOIN\n", str(LISTENING_PORT), "\n"])
    client_socket.sendall(join_msg.encode())

    peer_request = "LIST\n"
    client_socket.sendall(peer_request.encode())

    header_bytes = client_socket_helper.get_data_until_newline()
    header = header_bytes.decode()
    print("header:", header)

    if header != "PEERS":
        print("Invalid header, expected PEERS")
        exit(1)

    nodes = client_socket_helper.get_data_until_newline()
    print("peers:", nodes.decode())

    time.sleep(10)

    client_socket.close()
