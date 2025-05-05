
**Connection Method**

* We will use TCP sockets to communicate between nodes in the network so we don't need to worry about data corruption, dropped packets, and out-of-order packets.

**Tracker**

* The tracker's main thread will be responsible for listening to any incoming socket connections.

* When a peer connects to the tracker, it will spin up a new thread dedicated to the peer's connection since it will need to maintain multiple peer connections at once.
    * Adds this peer to some global list
    * At thread initialization, the tracker first waits for the peer to send a join message with the port the peer will be listening for other peers at. (Format: JOIN\n{Port No.}\n)
    * It then waits for the peer to send an ID message containing the peer's unique ID. It then registers the peer by adding the peer connection info to a map keyed on the peer's unique ID.
    * Each thread listens for a request from the peer to send the list of nodes so that the peer can know who to broadcast any new mined blocks to.
    * Message/serialization format: "LIST\n{IPAddress},{Port} {IP Address},{Port} {IP Address},{Port}...\n"
    * The thread can also process GET-PEER requests to get a peer's listening port so other peers know how to connect.
    * For GET-PEER requests, the tracker sends back the listening port with format "PEER-PORT\n{Port No.}\n". If the tracker did not find the port, then it
    sends back -1 as the port number.
    * This thread should also detect when a connection has closed -- done when a peer sends a LEAVE message or if it receives an empty payload from recv. When that happens it deletes the peer from the tracked peers and closes the thread.

**Peer**

The peer is responsible for maintaining its own copy of the blockchain, mining new nodes, and broadcasting them to its neighbors. The blockchain is a list of blocks, and will need a lock to ensure synchronization across different threads.

Block structure:

    {
            id:          // Block ID
            transaction: // Transaction data, see the Transaction struct below
            nonce:       // The nonce that needs to be solved for to mine a block
            prev_hash:   // The hash of the previous block
            hash:        // The hash of the current block    
     }

Transaction structure:

    {
        sender_id: // The public key aka id of the sender
        timestamp: // Time the transaction was added to the chain
        data:      // Transaction data (e.g. a vote)
        signature: // Signature over the data of the block
    }

Peer Initiation:
* When a peer joins the network, it connects to the tracker (based on the address and port passed as command line arguments) so the tracker knows that there is a new node in the network. The peer sends a message to the tracker with the port it will listen on so peers know how to connect (e.g. JOIN\n{Port No.}\n).

* The peer also generates an RSA public-private key pair, used for signing and allowing others to verify the signature. The public ID will also serve as the node's ID. The peer sends an ID message of format "ID {pub key no of bytes}\n{pub key bytes}\n" so the tracker can register the peer.

* The peer then requests a list of active peers from the tracker, and uses this list to request the longest chain in the network from all the peers using the GET-CHAIN request that the listening threads of the respective peers will handle (more on that later).

The peer will maintain a few different threads:

* Listening/Receiving thread to receive blocks from other nodes
    * Continuously listens for new connections -- in each connection it handles exactly one request.

    * When a peer connects, then there are two possible requests:
        * One is to add a block to the chain (request format of "BLOCK {no of block bytes}\n{block bytes}\n"). It adds this to a rcv buffer for another thread to consume.
        * Another is to retrieve the entire chain (request format of "GET-CHAIN\n"). It iterates through the entire chain, sending one block at a time (with the blockchain lock held) with format "BLOCK EXIST {no of bytes in block}\n{block}\n". Once it iterates through the chain, it'll send a dummy block with an ID of -1 to indicate the end of the chain.

    * After this request is handled, the connection is torn down and the thread goes back to listening for new connections, and only stops when it receives a shutdown signal.

* Thread to pull blocks of the rcv buffer:
    * This thread continuously listens for blocks being put on the rcv buffer by the listening thread.

    * Once it gets a block, then it'll check to see if the block is valid (recomputed hash has to match the hash sent, the difficulty is sufficient, and transaction signature is verified).

    * If it is a valid block, then it'll check whether it is a valid block to add to the chain (id is the next expected one, prev hash matches hash of latest block of the chain, and some logic specific to the voting application described in the application section)

    * If it is a valid block but can't be added to the chain (e.g. prev hash field doesn't match), and the incoming block's id is greater than or equal to the next expected ID, then this is a potential fork we need to resolve.
        * Requests list of nodes from the tracker
        * Requests every node from the peer using the GET-CHAIN request type. It will keep on receiving blocks from the peer until it hits the dummy block with ID -1 or if it finds that the chain sent from the peer is not a valid chain.

    * For invalid blocks or blocks where the id is less than the next expected ID, then discard the block.

* Mining thread:
    * We maintain a list of submitted transactions, and when the mining thread detects a transaction in the queue, then it'll take the transaction off the queue and mine a block by looking for a nonce that hashes out with the data to a value that has # of 0's == difficulty (difficulty is user-supplied). The hash is calculated over the nonce, transaction data, id, timestamp, and previous hash.

    * If we discover during mining that the id we're trying to mine for was already added to the chain (e.g. another peer mined it and broadcasted it), then we restart the mining process with the next id by adding the transaction back to the front of the queue. Same thing if we finish mining but don't add the block to the chain before the other peer gets to it.

* Main thread to handle create requests
    * The general way peer is used is an application will create a Peer object, which will do all the setup internally, and then use the peer object's create_txn API to submit a transaction.

    * This will add a transaction to the transaction queue for the mining thread to pull off of. (This allows us to use the console GUI without having to wait for the block to be mined)

    * After it adds the block to its chain, it will connect to the tracker to get a list of all the peers in the P2P network.

    * It will loop through all the peers and serialize + send the block and the peer's public key to each of the peers.

* Shutdown
    * The peer supports receiving a shutdown signal that will terminate all the threads and close any persistent sockets.
    * It also sends a LEAVE message to the Tracker.

**Application**

The application is a voting app that allows users to leverage blockchain for a more tamper-proof voting system.

The application allows a user to make two types of transactions:

1) Post a poll with: {Poll ID, Poll name, [category 1, category 2, ...]}. Poll ID is a randomly generated GUID and the name/categories are user supplied.

2) Vote on a posted poll, with the Poll ID as input.

When submitting a transaction that votes on a poll, the block is only valid if it corresponds to an existing poll. Otherwise the block will be discarded by the peers. (This is embedded at both the application and the peer layer)

When submitting a transaction that creates a poll, the block is only valid if a poll of the same name has not been created. Otherwise the block will be discarded by the peers. (This is embedded at both the application and the peer layer)

To aggregate the results, we iterate through the blockchain and aggregate the poll results across the poll IDs. This will effectively be the display (or console output) returned to the user.

Note that we allow users to vote on one option in a poll more than once (though the blockchain still internally keeps the user ID in each block, so the history of who voted for what is still preserved). This is primarily to facilitate testing, as testing larger number of transactions would lead to polls with lots of options or lots of polls, which would make it more difficult to check accuracy.

We offer a console-based GUI that allows users to view polls, create polls, vote on polls, and leave the network.