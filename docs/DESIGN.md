===Connection Method===

* We will use TCP sockets to communicate between nodes in the network so we don't need to worry about data corruption, dropped packets, and out-of-order packets.


===Tracker===

* The tracker's main thread will be responsible for listening to any incoming socket connections.

* When a peer connects to the tracker, it will spin up a new thread dedicated to the peer's connection.
    * Adds this peer to some global list
    * Each thread listens for a request from the peer to send the list of nodes so that the peer can know who to broadcast any new mined blocks to.
    * Message/serialization format: NODES\n<IP Address>,Port <IP Address>,Port <IP Address>,Port...\n
    * This thread should also detect when a connection has closed -- could be done by checking whether the return of recv() is None.

===Peer===

The peer is responsible for maintaining its own copy of the blockchain, mining new nodes, and broadcasting them to its neighbors. The blockchain is a list of blocks, and will need a lock to ensure synchronization across different threads.

Block structure:

{
    id:          // Block ID
    transaction: // Transaction data, see the Transaction struct below
    nonce:       // The nonce that needs to be solved for to mine a block
    prev_hash:   // The hash of the previous block
    hash:        // The hash of the current block

    signature:   // Signature over the data of the block
}

Transaction structure:

{
    timestamp: // Time the transaction was added to the chain
    data:      // Transaction data (e.g. a vote)
}

* When a peer joins the network, it connects to the tracker (based on the address and port passed as command line arguments) so the tracker knows that there is a new node in the network.

* The peer also generates an RSA public-private key pair, used for signing and allowing others to verify the signature.

* Forks will be resolved by majority vote

The peer will maintain a few different threads:

* Listening/Receiving thread to receive blocks from other nodes
    * Continuously polling non-blocking accept, grabbing a lock before accept to ensure that nothing gets sent to the peer its connected to in the other thread (see the last bullet of "Maint thread to handle create requests).

    * When a peer connects, then there are two possibilities:
        * One is to request the most recent block on the chain to help resolve forks
        * The other is a request to add a block to the node's current chain.

    * The node should receive a public key from its peer, which it'll use to verify the signature embedded within the block as an extra layer of verification.

    * The node will then recompute the hash over the data to ensure that the block is valid.

    * If the block is valid and there is no fork, then we add it to the current chain.

    * If there is a fork (when our current chain already has the block ID of a valid incoming block), then we have to get a list of all the peers from the tracker, and then request the most recent block on the chain from each pair and take the majority vote as the one we actually want to use for our chain.

* Main thread to handle create requests
    * When the application calls create(), then in the same application thread, the peer will mine a new block with the transaction data and add it to its chain.
        * Note that it is possible for it to receive a new block and add it to the chain before it finishes mining. So during the mining process it should periodically check to see if the block has already been mined, and if so, it should restart the mining process.

        * Mining will be finding a nonce such that the hash over all the data begins with 4 zeroes.

        * After the nonce has been calculated, a signature over the block data will be calculated using the private key.

    * After it adds the block to its chain, it will connect to the tracker to get a list of all the peers in the P2P network.

    * It will loop through all the peers and send the block and the peer's public key to each one of them.
        * We need locking between this part and the receiving thread, since the receiving thread could be temporarily connected to the same peer that the node is currently trying to send to.

===Application===

The application will be a voting app that allows users to leverage blockchain for a more tamper-proof voting system.

The application will allow the user to specify the category to vote on, and that counts as a transaction and triggers the node to mine a new block according to the protocol described above.

Aggregating the results is as simple as traversing the blockchain and summing together the results for each category.