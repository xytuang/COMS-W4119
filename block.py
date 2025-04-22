class Block:
    def __init__(self, _id, data, nonce, prev_hash, _hash):
        """
        Creates a block

        Args:
            _id (int): Block ID
            data (string): Data for this block
            nonce (int): the number that was mined, such that the hash criteria is met
            prev_hash (int): The hash number of this previous block
            _hash (int): The hash number of this block
        """
        self.id = _id
        self.data = data
        self.nonce = nonce
        self.prev_hash = prev_hash
        self.hash = _hash

    
    def is_valid(self):
        pass
    
    @staticmethod
    def mine(_id, data, prev_hash):
        """
        Finds a nonce given _id, data and prev_hash, and the hash for that nonce

        Args:
            _id (int): Block ID of this block
            data (string): data for this block
            prev_hash (int): hash of previous block
        
        Returns:
            A new Block object
        """
        pass
    
    def to_bytes(self):
        """
        Converts this block to byte representation
        """
        pass
    
    def to_string(self):
        """
        Converts this block to string representation. Useful for debugging
        """
        pass

    @staticmethod
    def from_bytes(message_body):
        """
        Returns a Block object from message_body (which is in bytes)
        Args:
            message_body (bytes): The byte representation of a block
        """
        pass



