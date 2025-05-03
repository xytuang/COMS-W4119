=====Outgoing Data Tamper Tests=====

Available tests: "hash", "prev_hash", "txn_data"

General test outline:

Start the tracker: python3 tracker.py 50000

Start the first peer: python3 app.py 50004 127.0.0.1 50000 2 config_empty.json tamper_TESTNAME_test/primary.txt

This creates a poll called pollA. Make sure to wait for the "pollA" creation transaction to be mined by checking list of available polls in input.
TESTNAME is one of "hash", "prev_hash", "txn_data"

Start the second peer: python3 app.py 50003 127.0.0.1 50000 2 tamper_hash_test/config.json tamper_TESTNAME_test/secondary.txt

This votes on pollA, but tampers with the data (every 3 blocks, starting from the first) before it gets transmitted to the peer. So the expectation is that we'll see the peer
reject the block.

However, the internal chain is consistent, just the outgoing data was tampered with. So we expect to see blocks being rejected in the first peer, but when the second peer mines a valid block and sends it to the first peer, the first peer is going to see that its chain is shorter (since the first peer doesn't actively mine anything beyond poll creation), and thus it'll request the chain from the second peer to adopt as its own chain. So in the end we'll see consistent vote results across both peers.


===Tamper Hash Test===

Observations match the expectation. 

First peer poll results:

Pick an option:
 1. Create poll
 2. Display available polls
 3. Vote for a poll
 4. See poll results
 5. Quit
4
Which poll do you want to see? pollA
{'a': 1, 'b': 3, 'c': 1}
-------------------------------------------

Second peer poll results:

Pick an option:
 1. Create poll
 2. Display available polls
 3. Vote for a poll
 4. See poll results
 5. Quit
4
Which poll do you want to see? pollA
{'a': 1, 'b': 3, 'c': 1}
-------------------------------------------

Highlighted logs from the first peer:

LOG poll_from_rcv_buffer: received invalid block, discarding <----(Rejecting the invalid hash)
... <----in between second peer mined a new block and broadcasted it
LOG get_chain_from_peer: Connected to peer. <----(Requesting the chain of the second peer)
LOG get_chain_from_peer: Requesting block ID 0
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 1
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 2
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 3
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 4
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 5
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 6
LOG get_chain_from_peer: Found end of chain.

Highlight logs from the second peer:

LOG mine: found a new block 4 <------ Mined a new block and tampered with the hash
LOG mine: found valid block, adding to chain
LOG mine: tampering with block (for testing)
LOG mine: tamper type: hash
... <-----in between a new block was mined
LOG process_peer_connections: Connected to new peer. <----(Sending the chain of the second peer)
LOG process_peer_connections: found header ['GET-BLOCK', '0']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '1']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '2']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '3']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '4']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '5']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '6']
LOG process_peer_connections: Listening thread terminated


===Tamper Prev Test===


Observations match the expectation. Pretty much the same output as the hash test,
which is to be expected.

First peer poll results:

Pick an option:
 1. Create poll
 2. Display available polls
 3. Vote for a poll
 4. See poll results
 5. Quit
4
Which poll do you want to see? pollA
{'a': 1, 'b': 3, 'c': 1}
-------------------------------------------

Second peer poll results:

Pick an option:
 1. Create poll
 2. Display available polls
 3. Vote for a poll
 4. See poll results
 5. Quit
4
Which poll do you want to see? pollA
{'a': 1, 'b': 3, 'c': 1}
-------------------------------------------

Highlighted logs from the first peer:

LOG poll_from_rcv_buffer: received invalid block, discarding <----(Rejecting the invalid hash)
... <----in between second peer mined a new block and broadcasted it
LOG get_chain_from_peer: Connected to peer. <----(Requesting the chain of the second peer)
LOG get_chain_from_peer: Requesting block ID 0
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 1
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 2
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 3
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 4
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 5
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 6
LOG get_chain_from_peer: Found end of chain.

Highlight logs from the second peer:

LOG mine: found a new block 4 <------ Mined a new block and tampered with the hash
LOG mine: found valid block, adding to chain
LOG mine: tampering with block (for testing)
LOG mine: tamper type: prev_hash
... <-----in between a new block was mined
LOG process_peer_connections: Connected to new peer. <----(Sending the chain of the second peer)
LOG process_peer_connections: found header ['GET-BLOCK', '0']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '1']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '2']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '3']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '4']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '5']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '6']
LOG process_peer_connections: Listening thread terminated

===Tamper Transaction Data Test===


Observations match the expectation. Pretty much the same output as the hash and prev_hash test,
which is to be expected.

First peer poll results:

Pick an option:
 1. Create poll
 2. Display available polls
 3. Vote for a poll
 4. See poll results
 5. Quit
4
Which poll do you want to see? pollA
{'a': 1, 'b': 3, 'c': 1}
-------------------------------------------

Second peer poll results:

Pick an option:
 1. Create poll
 2. Display available polls
 3. Vote for a poll
 4. See poll results
 5. Quit
4
Which poll do you want to see? pollA
{'a': 1, 'b': 3, 'c': 1}
-------------------------------------------

Highlighted logs from the first peer:

LOG poll_from_rcv_buffer: received invalid block, discarding <----(Rejecting the invalid hash)
... <----in between second peer mined a new block and broadcasted it
LOG get_chain_from_peer: Connected to peer. <----(Requesting the chain of the second peer)
LOG get_chain_from_peer: Requesting block ID 0
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 1
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 2
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 3
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 4
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 5
LOG get_chain_from_peer: Added block
LOG get_chain_from_peer: Connected to peer.
LOG get_chain_from_peer: Requesting block ID 6
LOG get_chain_from_peer: Found end of chain.

Highlight logs from the second peer:

LOG mine: found a new block 4 <------ Mined a new block and tampered with the hash
LOG mine: found valid block, adding to chain
LOG mine: tampering with block (for testing)
LOG mine: tamper type: txn_data
... <-----in between a new block was mined
LOG process_peer_connections: Connected to new peer. <----(Sending the chain of the second peer)
LOG process_peer_connections: found header ['GET-BLOCK', '0']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '1']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '2']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '3']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '4']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '5']
LOG process_peer_connections: Connected to new peer.
LOG process_peer_connections: found header ['GET-BLOCK', '6']
LOG process_peer_connections: Listening thread terminated

=====Blockchain Tamper Test=====

This tests what happens if a block already in the blockchain gets tampered with. A peer will create a poll and vote on a few options, but
at some point the chain's first block will be tampered with.

A new peer will then join the network and try to receive the longest chain (by default the first peer, since there are only two peers), but it will
reject the chain since it is invalid, demonstrating that the malignant copy will be localized to just the first peer.

python3 app.py 50004 127.0.0.1 50000 2 tamper_chain_test/config.json tamper_chain_test/primary.txt

Wait for all blocks to have been mined

python3 app.py 50003 127.0.0.1 50000 2

We see that in 50003_log.txt it detects the bad chain and does not adopt it.


=====Stress Test=====

Run in order:
python3 app.py 50004 127.0.0.1 50000 2 stress_test/config.json stress_test/primary.txt
python3 app.py 50003 127.0.0.1 50000 2 stress_test/config.json stress_test/secondary.txt
python3 app.py 50002 127.0.0.1 50000 2 stress_test/config.json stress_test/secondary.txt

This tests a bunch of transactions at the same time to make sure that we can handle concurrent execution fine. The peers don't always broadcast their blocks and periodically tamper with the hashes to really stress the system.

We see that at the end all peers have the same chain, which is what we want.