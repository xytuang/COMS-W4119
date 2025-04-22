class Transaction:
    def __init__(self, _id, sender, timestamp, data, signature=None):
        """

        Args:
            _id (int): Transaction ID
            sender (string): The peer that created this transaction. We need this so we can get the public key of the sender
            timestamp (float) Time at which transaction was created. Use time.time?
            data (string): Data for this particular transaction. Can be "vote for X" or something
            signature (bytes, optional): The signature for this transaction. Defaults to None.
        """
        self.id         = _id
        self.sender     = sender
        self.timestamp  = timestamp
        self.data       = data
        self.signature  = signature

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
        pass

    def sign(self, private_key):
        """
        Generates a signature from the byte representation of this transaction
        Args:
            private_key: The private key to use to sign this transaction
        
        Returns:
            A signature in bytes for this transaction
        """
        pass
    
    def verify(self, public_key):
        """
        Checks if this is a valid transaction by comparing its signature and the signature generated using the public key

        Args:
            public_key: The public key used to verify this transaction
        
        Returns:
            True if valid, False otherwise
        """
        pass
