class Blockchain:
    def __init__(self, chain=None, difficulty=4):
        """

        Args:
            chain (list | None): A list of Blocks. Used to initialize the blockchain of a peer that has just joined a network that has been mining.
            difficulty (int): the number of zeroes that a hash should start with
        """
        self.chain = chain if chain != None else []
        self.difficulty = difficulty

    def is_valid_block(self, block):
        """
        Checks if block is a valid block that can be added to the chain

        Checks include:
        1. Does the hash of block fulfil the difficulty criteria?
        2. Are the contents of block valid? ie. All transactions must have valid signatures
        3. Does prev_hash of block match the hash of the last block in the chain?

        Args:
            block (Block): The block to add

        Returns:
            bool: True if block can be added to the chain, False otherwise
        """
        block_hash = str(block.hash)
        
        # Check if hash for this block fulfils difficulty requirement
        if len(block_hash) < self.difficulty or block_hash[:self.difficulty] != "0" * self.difficulty:
            return False
        
        # Ok this can be modified later if needed.
        for transaction in block.data:
            valid_signature = transaction.verify()

            if not valid_signature:
                return False


        latest_block = self.get_latest_block()

        # If this is the very first block, return True
        if not latest_block:
            return True
        
        # Check if prev_hash of block is equal to hash of last block in the chain
        if latest_block.hash != block.prev_hash:
            return False
        
        return True

    def add_block(self, block):
        """
        Adds a block to the chain

        Args:
            block (Block): the block to add to the chain
        """
        self.chain.append(block)
    
    # TBH idk if we ever need to validate the entire chain
    def validate_chain(self):
        pass

    def get_latest_block(self):
        """
        Gets the last block in the chain or None if chain has no blocks

        Returns:
            latest_block (Block): The last block in the chain
        """
        latest_block = None

        if len(self.chain) > 0:
            latest_block = self.chain[-1]

        return latest_block
