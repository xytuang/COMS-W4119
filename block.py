import hashlib
import json

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

    
    def is_valid(self, difficulty):
        """
        Verifies whether this block is valid by
            1. recomputing the hash based on the block's contents
            2. checking if the hash starts with the required numebr of zeros (4 in our design)
        
        Args:
            difficulty (int) : number of leading zeros required for a hash
            
        Returns:
            bool: True if the block is valid; False if not
        """
        # This is concatenating the contents of the block to construct the same string used for mining
        block_string = (
            f"{self.id}"
            f"{self.data}"
            f"{self.nonce}"
            f"{self.prev_hash}"
        )
        
        # use the reconstructed string to recompute the hash
        recomputed_hash = hashlib.sha256(block_string.encode()).hexdigest()
        
        # check if the recomputed hash equals to the stoed hash inside the block
        if recomputed_hash != self.hash:
            return False
        
        # then, check if that hash starts with enough zeros
        return self.hash.startswith('0' * difficulty)
        
        
        
    
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



