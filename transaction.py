from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

class Transaction:
    def __init__(self, sender, timestamp, data, signature=None):
        """

        Args:
            sender (bytes): The byte representation of the public_key of the peer that created this transaction. We need this for verification
            timestamp (float) Time at which transaction was created.
            data (string): Data for this particular transaction. Can be "vote for X" or something
            signature (bytes, optional): The signature for this transaction. Defaults to None.
        """
        self.sender     = sender
        self.timestamp  = timestamp
        self.data       = data
        self.signature  = signature

    def to_string(self, with_signature=True):
        transaction_string = f"{self.sender.decode()}"
        transaction_string += f" {self.timestamp}"
        transaction_string += f" {self.data}"

        if with_signature and self.signature:
            transaction_string += f" {self.signature.hex()}"
        
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
        self.signature = private_key.sign(
            transaction_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    
    def verify(self):
        """
        Checks if this is a valid transaction by comparing its signature and the signature generated using the public key

        Args:
            public_key: The public key used to verify this transaction
        
        Returns:
            True if valid, False otherwise
        """
        # converts the byte representation in self.sender into a RSAPublicKey object
        public_key = serialization.load_pem_public_key(self.sender)
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