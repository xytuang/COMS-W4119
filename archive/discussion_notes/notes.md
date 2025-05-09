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




Longer chain scenario:

We start with

A: 1,2,3,4
B: 1,2,3,4
C: 1,2,3,4

Suppose B mines 5B
Suppose A manages to mine 5A
A also mines 6A immediately afterwards (by coincidence)

B sends 5B
A sends 5A and 6A


C gets 5B first and appends it to its blockchain

At this point, the current state is

A: 1,2,3,4,5A,6A
B: 1,2,3,4,5B
C: 1,2,3,4,5B

C gets 5A. This is a fork, so it sends out a chain request
C sees 6A but ignores it because it is waiting for a chain response
B replies with 5B
A replies with 6A

In our protocol, the majority chain is

1,2,3,4,5B

This means A is forced to re-mine for the transactions in 5A and 6A.


Edge case for majority at fork point failure:

Suppose we have:

A: 1,2,3,4,5A
B: 1,2,3,4,5B
C: 1,2,3,4,5C

A, B and C all send out their versions of Block 5.

They each send out their chain request.

There is no majority vote as there are 3 different versions of Block 5.

To handle this, look at the timestamps for each version of Block 5. Pick the earliest Block.


Another edge case for majority at fork point failure: (I'm pretty sure this shouldn't happen because the fork happens when they each send out Block 5)

Suppose we have:

A: 1,2,3,4,5A,6A
B: 1,2,3,4,5B
C: 1,2,3,4,5C

In the chain request,
A sends out 6A
B sends out 5B
C sends out 5C

There is no majority vote (split between 6A, 5B, 5C)

To handle this, look at the timestamps for each block. Pick the earliest block.



LONGEST CHAIN RULE:
Tbh, I think this is easier to implement

We start with

A: 1,2,3,4
B: 1,2,3,4
C: 1,2,3,4

A mines and broadcasts 5A
B mines and broadcasts 5B

C receives 5A and appends it to its chain

At this point, the current state is

A: 1,2,3,4,5A
B: 1,2,3,4,5B
C: 1,2,3,4,5A

C receives 5B and stores it in a separate alternate_chain variable

{
    5B
}

A receives 5B and stores it in a separate alternate_chain variable:

{
    5B
}

B receives 5A and stores it in a separate alternate_chain variable:

{
    5A
}

A mines and broadcasts 6A

C updates its alternate_chain variable

{
    5A -> 6A
}

B updates its alternate_chain variable

{
    5A -> 6A
}

B and C both see that the alternate chain is longer, and swap their main chain with alternate_chain


Additional notes: 
All peers continue mining based on the latest block in their main chain
When do we clean up old chains in alternate_chain?


Hypothetical scenario:

A: 1,2,3,4
B: 1,2,3,4
C: 1,2,3,4

B mines and sends out 5B
A mines 5A and 6A in succession and sends out both (right before it sees 5B)


A and C receive 5B.
B and C receive 5A and 6A.

A stores 5B in alternate_chain
B stores 5A->6A in alternate_chain
C stores 5A->6A in alternate_chain

B and C see that length of alternate_chain is longer than their main chain and switch to it.


Three-way fork with longest chain rule:

A: 1,2,3,4
B: 1,2,3,4
C: 1,2,3,4

A,B and C each mine and broadcast their own Block 5s.
Each update their alternate_chain like so:
A:
{
    5B
    5C
}

B:
{
    5A
    5C
}

C:
{
    5A
    5B
}

No switching occurs here

Suppose A mines and broadcasts 6A

B and C update their main chain after receiving 6A


Q: Do we need a frontend?

A: Nope, that's bonus. We can just use command-line arguments to create "interactivity".

I think this means creating files that contains predefined transactions for each peer.