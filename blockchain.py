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