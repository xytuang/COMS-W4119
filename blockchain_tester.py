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
        
        """