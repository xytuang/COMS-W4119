Test 1 (Basic Case):

Test 2 (Forking):

python3 tracker.py 50000

python3 app.py 50003 127.0.0.1 50000 1 (Peer 1)

* Create a poll
* Vote for an option in the poll
* Vote for an option in the poll

python3 app.py 50002 127.0.0.1 50000 1 (Peer 2)
* Create a poll

python3 app.py 50001 127.0.0.1 50000 1 (Peer 3)
* Do nothing

Now have Peer 1 vote on a poll

Expected outcome: Peer 2 and Peer 3 receive a block that indicates a higher amount of work,
so Peer 2 and Peer 3 both request Peer 1's chain and the fork is resolved.

Peer 2 and Peer 3 should now see Peer 1's chain when it views the set of available polls.