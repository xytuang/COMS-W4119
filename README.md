**Required dependencies**

This project uses the cryptography library and we need to install it.


If you are on Ubuntu/Debian, you need to install the following dependencies first. If you are on macOS/Windows, skip ahead to the Installation section.

1. build-essential

2. libssl-dev 

3. libffi-dev

4. python3-dev 

5. cargo

6. pkg-config

To install the above dependencies:
```code
sudo apt-get install build-essential libssl-dev libffi-dev \
    python3-dev cargo pkg-config
```

**Installation**

Once dependencies are installed, run the command below.

```code
pip install cryptography==35.0.0
```

**Files**

* `app.py`: application code for the voting app and is the driver code for peer functionality
* `peer.py`: code for the peer class and implements all the peer functionality (e.g. mining, forking, etc.)
* `blockchain.py`: helper class for representing a blockchain
* `block.py`: helper class for an individual block in the blockchain (encapsulates a transaction and adds additional data like hash, nonce, etc.)
* `transaction.py`: helper class for a transaction (the core data of the block)
* `tracker.py`: implementation of the tracker that helps peers find each other
* `enums.py`: some helpful enums we use in our code for tracking state
* `socket_helper.py`: wrapper class for a socket that helps abstract parts of reading TCP stream data

* `config_empty.json`: empty config file, used when you need to pass in a config file but don't want to inject any testing code (e.g. tampering with blocks). For testing purposes and used in the tests in TESTING.md.

* `*_test/`: Each folder corresponds to a different test. They contain any configuration/simulation files needed and also logs for each test. Please see TESTING.md for these tests, which includes details about usage and the test themselves.

* `archive/`: unused or old code/notes
* `docs/DESIGN.md`: description of our high level design
* `docs/TESTING.md`: description of the tests we ran

**How to run the code**

1. cd into the directory where tracker.py is and run tracker.py: `python3 tracker.py {tracker port}`

2. cd into the directory where app.py is and run app.py for each peer you want to create (one terminal per app.py): `python3 app.py {listening port} {tracker addr} {tracker port} {difficulty} {config file name} {sim file name}`

* {difficulty} is optional, default is 4.
* {config file name} is optional and for testing (but requires {difficulty} to be set).
* {sim file name} is optional and for testing (but requires {difficulty}, {config file name} to be set -- if you don't want to set any configs then the included `config_empty.json` can be used)

3. In app.py, there will be a console GUI presenting a list of options, and the user enters the number corresponding to the option to initiate the action.

4. To shutdown a peer, enter 5 when presented with the list of options in the GUI.

The config file is a .json that tells the code to periodically tamper with the blockchain data. This is used for testing only. An example config file:
`{
	"tamper_freq":3,
	"tamper_type":"hash",
	"broadcast_freq":2
}`

`tamper_freq` says how often a block should be tampered with, and `tamper_type` says what data should be tampered. `broadcast_freq` says how often a block should be broadcasted. If a block is not being broadcast, then tampering is skipped for that block.

The available types of tampering are "hash", "prev_hash", "txn_data" (transaction data), and "chain". "hash" modifies a broadcasted block's hash, "prev_hash"
the block's previous hash, and txn_data the block's transaction data. Note that these only modify an outgoing broadcasted block and not the underlying chain.

"chain" permanently invalidates the second block in the chain's data for the duration of the peer's existence. If the chain is less than 2 blocks long, then it won't do anything.

The sim file is a .txt file that allows the user to automate application commands, mainly used for testing. This is a newline separated file, where each line is one of three commands:

* `CREATE {poll name} {option1} {option2} {option3}...` (submits a transaction that creates a poll with the name and options)
* `VOTE {poll name} {option}` (submits a transaction that votes for the specified option on the specified poll)
* `SLEEP {sleep seconds}` 

**Assumptions Made**

1. Tracker does not go offline.
2. Tracker will be run first before any of the peers
3. For valid scenarios, peers should be started with the same difficulty
4. For this project, we assume a peer only talks to one tracker throughout its lifetime