from enum import Enum

"""
Some helpful enums, though only IDLE, WAITING_FOR_CHAIN and MINING are used.
"""

class State(Enum):
    IDLE                = 1  # Not doing anything
    WAITING_FOR_CHAIN   = 2  # Sent a chain request, waiting for peers to respond
    SYNCING             = 3  # Actively updating local blockchain (unused)
    MINING              = 4  # Mining a new block
    VALIDATING_BLOCK    = 5  # Verifying a block received from a peer (unused)
    SHUTTING_DOWN       = 6  # In the process of closing (unused)

class MessageTypes(Enum):
    TRACKER             = 1  # Message to/from tracker (peer registration, peer list)
    BLOCK               = 2  # A newly mined block
    CHAIN_REQUEST       = 3  # Asking others for latest block info
    CHAIN_RESPONSE      = 4  # Reply with latest block info
    CLOSE               = 5  # Indicates a peer is shutting down
    TRANSACTION         = 6  # New transaction to be added to mempool
    PING                = 7  # Heartbeat message to check liveness
    PEER_LIST           = 8  # Tracker's response with a list of active peers

