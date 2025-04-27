import hashlib
import json

class Block:
    def __init__(self, _id=None, data=None, nonce=None, prev_hash=None, _hash=None, timestamp=None):
        """
        Creates a block

        Args:
            _id (int): Block ID
            data (Transaction[]): Data for this block
            nonce (int): the number that was mined, such that the hash criteria is met
            prev_hash (int): The hash number of this previous block
            _hash (int): The hash number of this block
        """
        self.id = _id
        self.data = data
        self.nonce = nonce
        self.prev_hash = prev_hash
        self.hash = _hash
        self.timestamp = timestamp

    
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
        # Convert all transactions into string
        data_str = "\n".join(list(map(str, self.data)))
        # This is concatenating the contents of the block to construct the same string used for mining
        block_string = (
            f"{self.id}"
            f"{data_str}"
            f"{self.nonce}"
            f"{self.prev_hash}"
            f"{self.timestamp}"
        )
        
        # use the reconstructed string to recompute the hash
        recomputed_hash = hashlib.sha256(block_string.encode()).hexdigest()
        
        # check if the recomputed hash equals to the stoed hash inside the block
        if recomputed_hash != self.hash:
            return False
        
        # then, check if that hash starts with enough zeros
        if not (len(self.hash) < difficulty or self.hash.startswith('0' * difficulty)):
            return False
        
        for transaction in self.data:
            valid_signature = transaction.verify()

            if not valid_signature:
                return False

        return True
        
        
    @staticmethod
    def mine(_id, data, prev_hash, nonce, timestamp, difficulty = 4):
        """
        Finds a nonce given _id, data and prev_hash, and the hash for that nonce

        Args:
            _id (int): Block ID of this block
            data (string): data for this block
            prev_hash (int): hash of previous block
        
        Returns:
            A new Block object
        """
        data_str = "\n".join(list(map(str, data)))
        # construct the string to hash
        block_string = (
            f"{_id}"
            f"{data_str}"
            f"{nonce}"
            f"{prev_hash}"
            f"{timestamp}"
        )            
    
        # use the constructed string to compute the hash
        block_hash = hashlib.sha256(block_string.encode()).hexdigest()
        
        # check if hash meets the difficulty level
        if block_hash.startswith('0' * difficulty):
            return Block( # return the Block object if found a valid hash
                _id = _id,
                data = data,
                nonce = nonce,
                prev_hash = prev_hash,
                _hash = block_hash,
                timestamp = timestamp
            )
        return None
    
    def to_bytes(self):
        """
        Converts this block to byte representation for network transmission
        
        Returns:
            bytes: byte represenatation of this block
        """
        # use a dict to represent the block and convert it to json str
        data_str = "\n".join(list(map(str, self.data)))
        block_dict = {
            'id': self.id,
            'data': data_str,
            'nonce': self.nonce,
            'prev_hash': self.prev_hash,
            'hash': self.hash,
            'timestamp': self.timestamp
        }
        
        json_str = json.dumps(block_dict)
        
        return json_str.encode()
        
    
    def to_string(self):
        """
        Converts this block to string representation. Useful for debugging
        
        Returns:
            human-readable string rep of the block
        """
        data_str = "\n".join(list(map(str, self.data)))
        return (
            f"Block #{self.id}\n"
            f"Data: {data_str}\n"
            f"Nonce: {self.nonce}\n"
            f"Prev Hash: {self.prev_hash}\n"
            f"Hash: {self.hash}"
        )

    @staticmethod
    def from_bytes(message_body):
        """
        basically the reverse of to_bytes(), rebuild the Block object received over the network
        
        Returns:
            Block object from message_body (which is in bytes)
        
        Args:
            message_body (bytes): The byte representation of a block
        """
        
        try:
            # convert bytes to dict
            json_str = message_body.decode()
            block_dict = json.loads(json_str)
            
            # get all the stuff from the block
            block_id = block_dict['id']
            data_str = block_dict['data']
            data = data_str.split("\n")

            nonce = block_dict['nonce']
            prev_hash = block_dict['prev_hash']
            block_hash = block_dict['hash']
            timestamp = block_dict['timestamp']
            
            # return the block obj
            return Block(
                _id = block_id,
                data = data,
                nonce = nonce,
                prev_hash = prev_hash,
                _hash = block_hash,
                timestamp = timestamp
            )
            
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
            raise ValueError(f"Error parsing block from message: {e}")
            



