class Blockchain:
    def __init__(self, chain=None, difficulty=4):
        """

        Args:
            chain (list | None): A list of Blocks. Used to initialize the blockchain of a peer that has just joined a network that has been mining.
            difficulty (int): the number of zeroes that a hash should start with
        """
        self.chain = chain if chain != None else []
        self.difficulty = difficulty

    def add_block(self, block):
        """
        Adds a block to the chain

        Args:
            block (Block): the block to add to the chain
        """
        self.chain.append(block)
    
    def swap_block(self, new_block, public_key):
        """
        For handling forking
        Replaces the block with new_block._id with new_block.

        Args:
            new_block (Block): The new block to store

        Returns:
            Transaction[]: a list of transactions that need to re-mined and placed in a new block
        """
        swap_index = 0
        for i in range(len(self.chain)):
            blk = self.chain[i]
            if blk._id == new_block._id:
                swap_index = i
                break
        
        dropped_blocks = self.chain[swap_index:]
        self.chain = self.chain[:swap_index]
        
        
        # dropped_blocks can contain transactions that a specific peer did not create and we must distinguish them
        dropped_transactions = []
        for blk in dropped_blocks:
            for transaction in blk.data:
                if transaction.sender == public_key:
                    dropped_transactions.append(transaction)

        return dropped_transactions


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

    def get_block_by_id(self, _id):

        # If our chain is long enough and such a block actually exists in our chain, we return that block
        for i in range(len(self.chain)):
            curr_block = self.chain[i]
            if curr_block._id == _id:
                return curr_block

        # Else we return the latest block in our chain
        return self.get_latest_block()