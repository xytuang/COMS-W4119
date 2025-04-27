import json
import time
import uuid
from blockchain import Blockchain
from block import Block
from transaction import Transaction
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

class VotingApp:
    def __init__(self, peer):
        """
        Initialize the voting app with a reference to a peer
        
        Args:
            peer: the peer node this applicaiton is connected to
        """
        self.peer = peer
        
        # generate keys if needed but normally would come from the peer
        if not hasattr(peer, 'private_key') or not hasattr(peer, 'public_key'):
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )            
            self.public_key = self.private_key.public_key() # derive the public key from the private key
            
            self.public_key_bytes = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        
        else:
            # reuse the keys if the peer already got them
            self.private_key = peer.private_key
            self.public_key = peer.public_key

            self.public_key_bytes = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        
        if not peer:
            self.blockchain = Blockchain()
            if len(self.blockchain.chain) == 0:
                self.create_genesis_block()           
    
    def create_poll(self, poll_name, options):
        """
        Create a new poll
        
        Args:
            poll_name (str): The name of the poll
            options (list): List of candidates
            
        Returns:
            str: The ID of the newly created poll
        """
        poll_id = str(uuid.uuid4()) # a unique id for this poll
        
        transaction_data = {
            "transaction": "create_poll",
            "poll_id": poll_id,
            "poll_name": poll_name,
            "options": options
        }

        transaction_json = json.dumps(transaction_data)
        
        transaction = Transaction(
            sender = self.public_key_bytes,
            timestamp= time.time(),
            data = transaction_json
        )
        # sign the transaction
        transaction.sign(self.private_key)
        
        # create a block wit this transaction
        latest_block = self.peer.blockchain.get_latest_block()
        block_id = 0 if latest_block is None else latest_block.id + 1
        prev_hash = "0" * 64 if latest_block is None else latest_block.hash
        
        # mine the block (simplified)
        new_block = Block.mine(
            _id = block_id,
            data = transaction.to_string(),
            prev_hash = prev_hash
        )
        
        # add to chain
        self.peer.blockchain.add_block(new_block)
        
        # broadcast to peers
        print(f"Broadcasting new poll block: {poll_name}")
        self.peer.broadcast_block_to_all_peers(new_block)
        
        return poll_id
        
        
    def vote(self, poll_id, selected_option):
        """
        Vote on an existing poll
        
        Args:
            poll_id (str): The ID of the poll to vote on
            selected_option (str): The candidate to vote for
            
        Return:
            bool: True if vote is successful, false otw
        """
        # Create transaction data
        transaction_data = {
            "transaction_type": "vote",
            "poll_id": poll_id,
            "vote": selected_option
        }
        
        transaction_json = json.dumps(transaction_data)
        
        transaction = Transaction(
            sender = self.public_key_bytes,
            timestamp = time.time(),
            data = transaction_json
        )
        
        transaction.sign(self.private_key)
        
        latest_block = self.peer.blockchain.get_latest_block()
        block_id = 0 if latest_block is None else latest_block.id + 1
        prev_hash = "0" * 64 if latest_block is None else latest_block.hash
        
        new_block = Block.mine(
            _id=block_id,
            data=transaction.to_string(),
            prev_hash=prev_hash
        )                

        self.peer.blockchain.add_block(new_block)
        
        print(f"Broadcasting new vote block for poll {poll_id}")
        self.peer.broadcast_block_to_all_peers(new_block)
        
        return True

    def get_poll_results(self):
        """
        Get the results of all polls
        
        Return:
            dict: a dict containing poll results
        """
        return self.peer.blockchain.get_poll_results()
    
    def display_poll_results(self):
        """
        Display the poll results
        """
        poll_results = self.get_poll_results()
        
        if not poll_results:
            print("No polls found")
            return
        
        print("\n-----Election Results-----")
        for poll_id, poll_data in poll_results.items():
            print(f"\nElection: {poll_data['name']} (ID: {poll_id})")
            print("Candidates:")
            
            total_votes = sum(poll_data["vote_result"].values())
            # sort by votes
            sorted_candidates = sorted(
                poll_data["vote_result"].items(), 
                key=lambda item: item[1], 
                reverse=True
            )            
            
            for candidate, count in sorted_candidates:
                proportion = (count / total_votes * 100) if total_votes > 0 else 0
                print(f"    {candidate}: {count} votes ({proportion:.1f}%)")
            
# testing
class MockPeer:
    def __init__(self):
        self.blockchain = Blockchain()
        
        if len(self.blockchain.chain) == 0:
            genesis_block = self.blockchain.create_genesis_block()
            self.blockchain.add_block(genesis_block)
        
        # generate keys here, keeping it lightweight 
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.public_key = self.private_key.public_key()        
    
    def broadcast_block_to_all_peers(self, block):
        # keeping it lightweight so just print a msg
        print(f"Broadcasting block #{block.id} to all peers")


def test_voting_app():
    peer = MockPeer()
    app = VotingApp()
    
    # Create a presidential election
    print("\n=== Creating Presidential Election ===")
    president_poll_id = app.create_poll(
        "Presidential Election 2024",
        ["Presidential Candidate A", "Presidential Candidate B", "Presidential Candidate C"]
    )
    
    # Cast votes
    print("\n=== Casting Presidential Votes ===")
    app.vote(president_poll_id, "Candidate A")
    app.vote(president_poll_id, "Candidate B")
    app.vote(president_poll_id, "Candidate A")
    app.vote(president_poll_id, "Candidate C")
    app.vote(president_poll_id, "Candidate B")
    app.vote(president_poll_id, "Candidate A")
    app.vote(president_poll_id, "Candidate A")
    
    # Create a mayoral election
    print("\n=== Creating Mayoral Election ===")
    mayor_poll_id = app.create_poll(
        "Mayoral Election 2024",
        ["Mayor Candidate X", "Mayor Candidate Y", "Mayor Candidate Z"]
    )
    
    # Cast votes
    print("\n=== Casting Mayoral Votes ===")
    app.vote(mayor_poll_id, "Mayor Candidate X")
    app.vote(mayor_poll_id, "Mayor Candidate Z")
    app.vote(mayor_poll_id, "Mayor Candidate X")
    app.vote(mayor_poll_id, "Mayor Candidate Y")
    app.vote(mayor_poll_id, "Mayor Candidate Y")
    
    # Display results
    app.display_poll_results()
    
    # Verify blockchain integrity
    print("\n=== Blockchain Integrity ===")
    print(f"Chain length: {len(peer.blockchain.chain)} blocks")
    print(f"Is blockchain valid: {peer.blockchain.validate_chain() if hasattr(peer.blockchain, 'validate_chain') else 'N/A'}")

if __name__ == "__main__":
    test_voting_app()