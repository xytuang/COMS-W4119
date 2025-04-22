Q: Is it ok to for all peers to talk to each directly? Should we use intermediate nodes for scaling?

A: Peer gets list of all other peers from tracker and sends it to those peers. I assume we don't need intermediate nodes then.



Q: Will tracker go offline?

A: No, but there are bonus points for a distributed tracker (let's not do this, it's pretty hard.)



Q: When to do mining? Should mining only start when there is a new transaction?

A: Do not mine when there is no new data to send. The workflow should be as such:

New vote/transaction -> Start mining -> Create new block -> Check new block is valid -> Append block to local blockchain -> Broadcast block

The above workflow assumes that every block contains a single transaction. We could have multiple transactions in a single block.



Q: Forking

A: The TA's answer was slightly different from what we initially thought but here's an example.

Suppose we have three peers, all of them have blocks 1,2,3,4

A: 1,2,3,4
B: 1,2,3,4
C: 1,2,3,4

Suppose A and B create and send out block 5 at the same time.

A receives B's block 5.
A stores it temporarily.
A sends out a "chain request" message.

B receives A's block 5.
B stores it temporarily.
B sends out a "chain request" message.

C receives A's block 5 first. C appends A's block 5 to its local blockchain.
C then receives B's block 5.
C sends out a "chain request" message.

At this point in time, this is the current state of each peer.

A: 1,2,3,4,5A (stores 5B somewhere else)
B: 1,2,3,4,5B (stores 5A somewhere else)
C: 1,2,3,4,5A (stores 5B somewhere else)


A "chain request" message is indicated by a header field, and contains the hash and id of the latest block.

A's chain request: id: 5, hash: hash(5A)
B's chain request: id: 5, hash: hash(5B)
C's chain request: id: 5, hash: hash(5A)

Each peer gets all the chain request messages of other peers before coming to a decision.
We need to ensure that all peers stay open during this process as we don't want to wait indefinitely for a 
request message from a peer that has suddenly closed.

A sees that majority of the peers on the blockchain have 5A as the latest block, so nothing changes for A.
C sees that majority of the peers on the blockchain have 5A as the latest block, so nothing changes for C.
B sees that majority of the peers on the blockchain have 5A as the latest block, so it must replace 5B with 5A.
At this point, B MUST mine for a new block with the transactions stored in 5B. This means we must maintain a variable that stores unsent transactions.

The above logic handles the case where there are no malicious peers and all peers have blockchains of the same length.


The malicious scenario:

We start with

A: 1,2,3,4
B: 1,2,3,4
C: 1,2,3,4

Suppose A is the malicious peer.
A and B send block 5 at the same time. (5A is a malicious block)

C gets 5A first.
C checks if 5A is a valid block.
Checking if 5A is a valid block means the following:
- Does the prev hash of 5A match the hash of 4?
- Does the hash of 5A fulfil the hash criteria? ie. Does it start with 4 zeroes?
- Are the transactions in 5A signed correctly?

The last check (signature check) requires a public/private key for each peer.
Signing correctly means that each transaction has been signed by the owner of the asset.
Suppose 5A contains the transaction "B voted for candidate X <some incorrect signature y>".
C will verify if signature y using B's public key. If the signature is incorrect, C discards 5A.

Since 5A is malicious, C rejects 5A.

C sends out a chain request immediately.

C gets 5A and rejects it immediately.

C gets 5B and accepts it.

On acceptance, C broadcasts that it has 5B as its latest block. Note that this broadcast is not needed if no updates were made.

Note: If B's initial 5B broadcast gets mixed into the stream, we can just ignore it because we are in the middle of a chain request.





Q: Do we need a frontend?

A: Nope, that's bonus. We can just use command-line arguments to create "interactivity".

I think this means creating files that contains predefined transactions for each peer.