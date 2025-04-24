class Peer:
    def __init__(self, tracker_addr, peer_addr, transaction_file=None):
        self.sock
        self.tracker_addr
        self.blockchain
        self.public_key
        self.private_key
        self.state
        self.outgoing_messages
        self.incoming_messages
        self.transactions

        self.send_thread
        self.receive_thread
        self.mine_thread

        self.log_file

    def handle_send(self):
        pass
    
    def handle_receive(self):
        pass

    def handle_mine(self):
        pass