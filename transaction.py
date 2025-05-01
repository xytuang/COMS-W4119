from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
import json

class Transaction:
    def __init__(self, sender, timestamp, data, signature=None):
        """

        Args:
            sender (bytes): The byte representation of the public_key of the peer that created this transaction. We need this for verification
            timestamp (float) Time at which transaction was created.
            data (dict): Data for this particular transaction.
            signature (bytes, optional): The signature for this transaction. Defaults to None.
        """
        self.sender     = sender
        self.timestamp  = timestamp
        self.data       = data
        self.signature  = signature

    def to_json(self, with_signature=True):
        txn_dict = {
            "sender": self.sender.decode(),
            "timestamp": self.timestamp,
            "data": self.data
        }

        if with_signature:
            txn_dict["signature"] = self.signature.hex()
        return txn_dict
    
    @staticmethod
    def from_json(obj):
        return Transaction(
            sender=obj["sender"].encode(),
            timestamp=obj["timestamp"],
            data=obj["data"],
            signature=bytes.fromhex(obj["signature"]) if obj["signature"] else None
        )


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
        txn_dict = self.to_json(with_signature)
        txn_json_str = json.dumps(txn_dict, sort_keys=True)
        return txn_json_str.encode()

    @staticmethod
    def from_bytes(txn_bytes):
        txn_json_str = txn_bytes.decode()
        txn_dict = json.loads(txn_json_str)

        return Transaction(
            sender=txn_dict["sender"].encode(),
            timestamp=txn_dict["timestamp"],
            data=txn_dict["data"],
            signature=bytes.fromhex(txn_dict["signature"]) if txn_dict["signature"] else None
        )



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

    def to_string(self, with_signature=True):
        """
        Returns a string representation of the Transaction object.
        """
        txn_dict = self.to_json(with_signature)
        txn_str = json.dumps(txn_dict, indent=4)
        return txn_str

    def __str__(self):
        return self.to_string()