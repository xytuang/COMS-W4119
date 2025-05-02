from block import Block
import json

"""
Transaction format for the polling application

1. For creating a poll:
{
    "transaction_type": "create_poll",
    "poll_id": "unique_id",
    "poll_name": "Question text",
    "options": ["Option 1", "Option 2", "Option 3", "..."]
}

2. For voting:
{
    "transaction_type": "vote",
    "poll_id": "unique_id",
    "vote": "Option selected"
}
"""

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


    def can_add_block_to_chain(self, new_block):
        if new_block.id != len(self.chain):
            print("LOG can_add_block_to_chain: rejected block due to invalid block id")
            return False

        if len(self.chain) == 0:
            return True

        latest_block_hash = self.get_latest_block().hash
        if latest_block_hash != new_block.prev_hash:
            print("LOG can_add_block_to_chain: rejected block due to invalid hash")
            return False

        if self.is_new_block_repeat_poll(new_block):
            return False

        return True

    def is_new_block_repeat_poll(self, new_block):
        print("new_block.txns[0].data:", new_block.txns[0].data)
        if "poll_name" in new_block.txns[0].data:
            print("new_block.txns[0].data:", new_block.txns[0].data)
            for block in self.chain:
                print("\tblock.txns[0].data:", block.txns[0].data)
                if "poll_name" in block.txns[0].data:
                    if block.txns[0].data["poll_name"] == new_block.txns[0].data["poll_name"]:
                        print("LOG can_add_block_to_chain: rejected block due to existing poll")
                        return True
        return False


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
            if curr_block.id == _id:
                return curr_block

        # Else there is no block and return None
        return None
    
    
    def create_block(self, data):
        """
        Create a new block with the given data and add it to the chain
        
        Args:
            data (str or Transaction): The data to be included in the new block
            
        Returns:
            Block: the newly created and added block
        """
        latest_block = self.get_latest_block()
        new_block_id = 0 if latest_block is None else latest_block.id + 1
        new_block_prev_hash = "0" * 64 if latest_block is None else latest_block.hash
        
        # start mining the new block
        new_block = Block.mine(
            _id = new_block_id,
            data = data,
            prev_hash = new_block_prev_hash,
            difficulty = self.difficulty
        )
        
        # add the block to chain
        self.add_block(new_block)
        
        return new_block
        
    # I am not 100% sure if this is needed but from some videos I watched this is
    # considered a special block and it's easy to implement so i did it anyway
    def create_genesis_block(self):
        """
        Create the first block in the chain
        
        Returns:
            Block: the gensis block
        """
        genesis_block = Block.mine(
            _id = 0,
            data = "",
            prev_hash = "0" * 64,
            difficulty = self.difficulty            
        )
        
        self.add_block(genesis_block)
        return genesis_block
    
    def get_poll_results(self):
        """
        Iterates through the blockchain and aggregate the poll results
        
        Returns:
            dict: A dictionary with poll info and vote counts (key: poll_id, value: poll results)
        """
        
        polls_result = {}
        
        for block in self.chain:
            try:
                transaction = json.loads(block.data)
                if "transaction_type" in transaction:
                
                    # case 1: block's transaction contains poll creation
                    if transaction["transaction_type"] == "create_poll":
                        # get the info of this poll
                        poll_id = transaction["poll_id"]
                        poll_name = transaction["poll_name"]
                        options = transaction["options"]
                        
                        # initialize this poll in dict
                        polls_result[poll_id] = {
                            "name": poll_name,
                            "options": options,
                            "vote_result": {option: 0 for option in options} # initialize vote : 0 for every option
                        }

                    # case 2: block's transaction contains vote
                    elif transaction["transaction_type"] == "vote":
                        poll_id = transaction["poll_id"]
                        voted_option = transaction["vote"]
                        
                        # add vote to the poll
                        if (poll_id in polls_result and 
                            voted_option in polls_result[poll_id]["vote_result"]):
                            
                            polls_result[poll_id]["vote_result"][voted_option] += 1
                    
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                # ignore blocks that contains invalid json (including genesis)
                continue
            
        return polls_result
