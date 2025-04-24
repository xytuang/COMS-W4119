
class SocketHelper():
    """
    The core socket logic for recieving messages with our self-made protocol.
    Makes the overall project logic a lot simpler as long as get_header and get_data
    are implemented correctly since it'll handle cases such as two messages being
    combined in one packet via keeping self.rem_buf as state.

    Client and server both recieve messages so their own respective socket helpers
    inherit this and implement their own specific behaviors on top.
    """

    def __init__(self, socket):
        self.socket = socket
        self.rem_buf = None

    def get_data_until_newline(self):
        """
        Retrieves data until it sees a newline delimiter.
        """
        curr_buf = b''
        while True:
            tried_to_recv = False
            rec_buf = None

            # Read the unparsed buf from previous receives
            if self.rem_buf != None:
                rec_buf = self.rem_buf
                self.rem_buf = None
            else:
                tried_to_recv = True
                rec_buf = self.socket.recv(2048)

            # Means the socket disconnected
            if tried_to_recv and not rec_buf:
                return None

            idx = rec_buf.find(b'\n')
            buf_len = len(curr_buf)
            curr_buf += rec_buf

            if idx != -1:
                break

        buf_idx = idx + buf_len
        if idx < len(rec_buf) - 1:
            self.rem_buf = rec_buf[idx+1:]
        # Don't want to include the newline so don't include buf_idx
        header = curr_buf[:buf_idx]
        return header

    # TODO: Might not need depending on our protocol
    def get_n_bytes_of_data(self, n_bytes):
        """
        Recieves n_bytes of data

        arguments:
        n_bytes -- number of bytes in data
        """
        curr_buf = b''
        msg_len = 0
        while True:
            rec_buf = None

            # Read the unparsed buf from previous receives
            if self.rem_buf != None:
                rec_buf = self.rem_buf
                self.rem_buf = None
            else:
                rec_buf = self.socket.recv(4096)

            msg_len += len(rec_buf)
            curr_buf += rec_buf

            if msg_len >= n_bytes:
                break

        if msg_len > n_bytes:
            self.rem_buf = curr_buf[n_bytes:]

        data = curr_buf[:n_bytes]
        return data