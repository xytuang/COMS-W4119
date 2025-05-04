For testing, we use difficulty 2 (e.g. nonce is valid when the first two digits of the hash are 0) for testing convenience.

=====Basic Test=====

This test is manual and is just a simple test to make sure basic functionality works. All data is untampered with for this test, and all blocks are broadcast immediately after they are mined.

Start the tracker: python3 tracker.py 50000

Start the first peer: python3 app.py 50004 127.0.0.1 50000 2
Start the second peer: python3 app.py 50003 127.0.0.1 50000 2
Start the third peer: python3 app.py 50002 127.0.0.1 50000 2

Peer 1 input: 1, create pollA with options a,b,c
Peer 1 input: 3, vote for pollA, option a

Wait a few seconds for the blocks to be mined.

Peer 2 input: 4, view pollA

We expect a to have 1 vote.

Peer 3 input: 4, view pollA

We expect a to have 1 vote.

Peer 2 input: 3, vote for pollA, option b

Wait a few seconds for the vote transaction block to be mined.

Peer 1 input: input 4, view pollA

We expect a and b to each have one vote.

Peer 2 input: input 4, view pollA

We expect a and b to each have one vote.

Peer 3 input: input 4, view pollA

We expect a and b to each have one vote.

Peer 1 input: 1, create pollB with options x,y

Peer 1 input: 3, vote for pollB, option x

Wait a few seconds for the vote transaction block to be mined

Peer 1 input: input 4, view pollB

We expect x to have one vote.

Peer 2 input: input 4, view pollB

We expect x to have one vote.

Peer 3 input: input 4, view pollB

We expect x to have one vote.

Observations: We see the expected behavior in the console. Logs are also included, and they show new blocks created (for poll creation and votes) and broadcasted when the respective peer mines them, as well as the peer recieving them.

Logs are in the basic_test folder.

=====Peer Joining Test=====

Start the tracker: python3 tracker.py 50000

Start the first peer: python3 app.py 50002 127.0.0.1 50000 2

Peer 1 input: 1, create pollA with options a,b,c
Peer 1 input: 3, vote for pollA, option a
Peer 1 input: 3, vote for pollA, option b
Peer 1 input: 3, vote for pollA, option c

Wait a few seconds for the blocks to be mined

Start the second peer: python3 app.py 50003 127.0.0.1 50000 2

Start the third peer: python3 app.py 50004 127.0.0.1 50000 2

For all peers: input 4, view pollA

Should see a,b,c with one vote each.

Observations: When peers 2 and 3 join, they recieve the longest chain in the network. In this case this is Peer 1. We see in the included logs that Peer 1 mines the two blocks, and then serves GET-BLOCK requests to Peers 2 and 3. For Peer 2 we see it requesting the chain from 1 but also sending its chain to Peer 3 when Peer 3 joins so that Peer 3 can choose the longest chain it receives. And in Peer 3 logs we see it requesting chains from 1 and 2.

Logs are in the peer_join_test folder.

=====Peer Leaving Test=====

Start the tracker: python3 tracker.py 50000

Start the first peer: python3 app.py 50002 127.0.0.1 50000 2
Start the second peer: python3 app.py 50003 127.0.0.1 50000 2
Start the third peer: python3 app.py 50004 127.0.0.1 50000 2

Peer 1 input: 1, create pollA with options a,b,c

For Peer 2 and Peer 3 input: 4, view pollA

We expect pollA to exist with no votes.

Peer 1 input: 5 (peer exits and leaves)

Peer 2 input: 3, vote for pollA, option a

For Peer 2 and Peer 3 input: 4, view pollA

We expect pollA to have one vote for a.

Observations: We see the expected behavior, and it shows that the network can handle the leaving of the peer. In our case, the peer that created the poll left, but since the other peers had a copy of the blockchain in their own nodes, they were still able to vote on the poll and have it be consistent across the remaining two peers without issue.

Logs are in the peer_leave_test folder.

=====Fork Test=====

Start tracker: Start the tracker: python3 tracker.py 50000

Start Peer 1: python3 app.py 50003 127.0.0.1 50000 2 demo_fork_test/config.json

Peer 1 input: 1, create pollA, options a,b,c

Start Peer 2: python3 app.py 50004 127.0.0.1 50000 2
Start Peer 3: python3 app.py 50002 127.0.0.1 50000 2

Peer 1 input: 3, vote for pollA, option a (block not broadcasted)
Peer 1 input: 3, vote for pollA, option a (block not broadcasted)

Since Peer 1 does not broadcast these blocks, Peers 2 and 3 will still have pollA with no votes.

Peer 2 input: 3, vote for pollA, option a

Peer 2 will only have one vote for option a in pollA.

Peer 1 input: 3 vote for pollA, option b (block gets broadcasted)

Wait a few seconds and check that Peers 1,2 and 3 all have the same chain (a has 2 votes, b has 1 vote, c has no votes).

When Peer 1 broadcasts the option b vote, forking happens in Peers 2/3 since Peer 1's internal chain is longer (just not broadcasted yet), and that causes Peers 2/3 to request Peer 1's chain to replace their own shorter chain.

Logs are in the demo_fork_test folder.


=====Basic Simulation Test=====

This is another basic functionality test, except this time the tests take in a simulation file that will allow the peers to automatically run commands rather than relying solely manual input.

Start the tracker: python3 tracker.py 50000

Peer 1: python3 app.py 50003 127.0.0.1 50000 2 config_empty.json basic_sim_test/primary.txt
Wait for a few seconds
Peer 2: python3 app.py 50002 127.0.0.1 50000 2 config_empty.json basic_sim_test/secondary.txt
Peer 3: python3 app.py 50004 127.0.0.1 50000 2 config_empty.json basic_sim_test/secondary.txt 

Main thing to check here is that the nodes end up with the same result. Inputting 4 and checking pollA for each of the nodes reveal that this is indeed the case case (detailed logs also included).

Logs are in the basic_sim_test.

=====Outgoing Data Tamper Tests=====

Available tests: "hash", "prev_hash", "txn_data"

General test outline:

Start the tracker: python3 tracker.py 50000

Start the first peer: python3 app.py 50004 127.0.0.1 50000 2 config_empty.json tamper_TESTNAME_test/primary.txt where TESTNAME is one of "hash", "prev_hash", "txn_data".

This creates a poll called pollA. Make sure to wait for the "pollA" creation transaction to be mined by checking list of available polls in input.

Start the second peer: python3 app.py 50003 127.0.0.1 50000 2 tamper_hash_test/config.json tamper_TESTNAME_test/secondary.txt

This votes on pollA, but tampers with the data (every 3 blocks, starting from the first) before it gets transmitted to the peer. So the expectation is that we'll see the peer
reject the block.

However, the internal chain is consistent, just the outgoing data was tampered with. So we expect to see blocks being rejected in the first peer, but when the second peer mines a valid block and sends it to the first peer, the first peer is going to see that its chain is shorter (since the first peer doesn't actively mine anything beyond poll creation), and thus it'll request the chain from the second peer to adopt as its own chain. So in the end we'll see consistent vote results across both peers.

Logs are in the tamper_TESTNAME_test folder.

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

Logs are in the tamper_chain_test folder.

=====Stress Test=====

Run in order:
python3 tracker.py 50000
python3 app.py 50004 127.0.0.1 50000 2 stress_test/config.json stress_test/primary.txt
python3 app.py 50003 127.0.0.1 50000 2 stress_test/config.json stress_test/secondary.txt
python3 app.py 50002 127.0.0.1 50000 2 stress_test/config.json stress_test/secondary.txt

This tests a bunch of transactions at the same time to make sure that we can handle concurrent execution fine. The peers don't always broadcast their blocks and periodically tamper with the hashes to really stress the system.

Peers will race against each other by nature of this test, so this is a good way to stress our forking logic to the max. We expect to see all the peers converge on the same chain in the end, and we observe the same console output for each of the peers once all the transactions have been processed:

Pick an option:
 1. Create poll
 2. Display available polls
 3. Vote for a poll
 4. See poll results
 5. Quit
4
Which poll do you want to see? pollA
{'a': 34, 'b': 54, 'c': 53}

We see that at the end all peers have the same chain, which is what we want.

Logs are in the stress_test folder.