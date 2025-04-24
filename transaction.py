from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

class Transaction:
    def __init__(self, sender, timestamp, data, signature=None):
        """

        Args:
            sender (string): The peer that created this transaction. We need this so we can get the public key of the sender
            timestamp (float) Time at which transaction was created. Use time.time?
            data (string): Data for this particular transaction. Can be "vote for X" or something
            signature (bytes, optional): The signature for this transaction. Defaults to None.
        """
        self.sender     = sender
        self.timestamp  = timestamp
        self.data       = data
        self.signature  = signature

    def to_string(self, with_signature=True):
        transaction_string = ""
        transaction_string += f"sender:{self.sender}\n"
        transaction_string += f"timestamp:{self.timestamp}\n"
        transaction_string += f"data:{self.data}\n"

        if with_signature:
            transaction_string += f"signature:{self.signature}\n"
        
        return transaction_string

    def to_bytes(self, with_signature=True):
        """
        Converts this transaction to bytes

        Args:
            with_signature (bool, optional): 
                                            Indicates whether to include the signature when converting this transaction to bytes. 
                                            Defaults to True.
        Returns:
            A byte representation of this transaction
        """
        transaction_string = self.to_string(with_signature)
        return transaction_string.encode()

    def sign(self, private_key):
        """
        Generates a signature from the byte representation of this transaction and updates self.signature
        Args:
            private_key: The private key to use to sign this transaction
        
        Returns:
            A signature in bytes for this transaction
        """
        transaction_bytes = self.to_bytes(False)
        signature = private_key.sign(
            transaction_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        self.signature = signature

        
    
    def verify(self, public_key):
        """
        Checks if this is a valid transaction by comparing its signature and the signature generated using the public key

        Args:
            public_key: The public key used to verify this transaction
        
        Returns:
            True if valid, False otherwise
        """
        transaction_bytes = self.to_bytes(False)

        # verify raises an InvalidSignature Exception if the verification fails
        try:
            public_key.verify(
                self.signature,
                transaction_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except:
            return False

    def __str__(self):
        return self.to_string()