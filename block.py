import hashlib
import json
from transaction import Transaction

class Block:
    def __init__(self, _id=None, txns=None, nonce=None, prev_hash=None, _hash=None, timestamp=None):
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
        self.txns = txns
        self.nonce = nonce
        self.prev_hash = prev_hash
        self.hash = _hash
        self.timestamp = timestamp
    
    def to_json(self, with_hash=True):
        block_dict = {
            "id": self.id,
            "txns": [txn.to_json() for txn in self.txns],
            "nonce": self.nonce,
            "prev_hash": self.prev_hash,
            "timestamp": self.timestamp
        }
        if with_hash:
            block_dict["hash"] = self.hash

        return block_dict
    
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
        block_bytes = self.to_bytes(False)

        # use the reconstructed string to recompute the hash
        recomputed_hash = hashlib.sha256(block_bytes).hexdigest()
        
        # check if the recomputed hash equals to the stoed hash inside the block
        if recomputed_hash != self.hash:
            print("LOG block.is_valid: recomputed hash:", recomputed_hash)
            print("LOG block.is_valid: own hash:", self.hash)
            print("LOG block.is_valid: recomputed hash not same as current hash")
            return False
        
        # then, check if that hash starts with enough zeros
        if not (len(self.hash) < difficulty or self.hash.startswith('0' * difficulty)):
            print("does  not meet difficulty")
            return False
        
        for txn in self.txns:
            valid_signature = txn.verify()

            if not valid_signature:
                print("invalid signature")
                return False

        return True
        
        
    @staticmethod
    def mine(_id, txns, prev_hash, nonce, timestamp, difficulty):
        """
        Finds a nonce given _id, data and prev_hash, and the hash for that nonce

        Args:
            _id (int): Block ID of this block
            data (string): data for this block
            prev_hash (int): hash of previous block
        
        Returns:
            A new Block object
        """
        block = Block(_id, txns, nonce, prev_hash, timestamp=timestamp)
        block_bytes = block.to_bytes(False)        
    
        # use the constructed string to compute the hash
        block_hash = hashlib.sha256(block_bytes).hexdigest()
        
        # check if hash meets the difficulty level
        if block_hash.startswith('0' * difficulty):
            block.hash = block_hash
            return block
        
        return None
    
    def to_bytes(self, with_hash=True):
        """
        Converts this block to byte representation for network transmission
        
        Returns:
            bytes: byte represenatation of this block
        """
        # use a dict to represent the block and convert it to json str
        block_dict = self.to_json(with_hash)        
        json_str = json.dumps(block_dict, sort_keys=True)
        return json_str.encode()

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
            txns = [Transaction.from_json(txn) for txn in block_dict["txns"]]
            nonce = block_dict['nonce']
            prev_hash = block_dict['prev_hash']
            block_hash = block_dict['hash']
            timestamp = block_dict['timestamp']
            
            # return the block obj
            return Block(
                _id = block_id,
                txns = txns,
                nonce = nonce,
                prev_hash = prev_hash,
                _hash = block_hash,
                timestamp = timestamp
            )
            
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
            raise ValueError(f"Error parsing block from message: {e}")
            



