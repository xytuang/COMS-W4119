import sys
import uuid

from peer import Peer


def find_poll(peer, poll_identifier, using_id=True):
    """
    Finds a poll by identifier

    Args:
        peer (Peer): underlying peer object for this client
        poll_name (str): the name to find

    Returns:
        dict: A dictionary describing the poll, with its id, name and options
    """
    poll_field = "poll_id" if using_id else "poll_name" 
       
    for block in peer.blockchain:
        for txn in block.txns:
            txn_data = txn.data
            if txn_data[poll_field] == poll_identifier and txn_data["transaction_type"] == "create_poll":
                return txn_data
    return None

def get_all_polls(peer):
    """
    Display all ongoing polls

    Args:
        peer (Peer): _description_

    Returns:
        _type_: _description_
    """
    polls = []
    for block in peer.blockchain:
        for txn in block.txns:
            txn_data = txn.data
            if txn_data["transaction_type"] == "create_poll":
                polls.append(txn_data)
    
    return polls

def get_poll_results(peer, poll_id):
    """_summary_

    Args:
        peer (Peer): underlying peer object for this client
        poll_id (str): Used to compare with poll_id field of each transaction

    Returns:
        dict: A map of counts for each option in the poll
    """
    poll = find_poll(peer, poll_id, True)
    if not poll:
        return None
    
    options_count = {option: 0 for option in poll["options"]}

    for block in peer.blockchain:
        for txn in block.txns:
            txn_data = txn.data
            if txn_data["poll_id"] == poll_id and txn_data["transaction_type"] == "vote":
                voted_option = txn_data["vote"]
                options_count[voted_option] += 1
    
    return options_count

    
def create_poll(peer, poll_name, poll_options):
    """

    Args:
        peer (Peer): underlying peer object for this client
        poll_name (str): name of poll to create
        poll_options (list): a list of available options for this poll
    """
    poll_id = str(uuid.uuid4())
    poll_dict = {
        "transaction_type": "create_poll",
        "poll_id": poll_id,
        "poll_name": poll_name,
        "options": poll_options
    }
    peer.create_txn(poll_dict)

def vote(peer, poll_id, option):
    """
    Args:
        peer (Peer): underlying peer object for this client
        poll_id (str): id of poll that this vote is for
        option (str): which option of the poll this vote is for
    """
    vote_dict = {
        "transaction_type": "vote",
        "poll_id": poll_id,
        "vote": option
    }
    peer.create_txn(vote_dict)


if __name__ == '__main__':
    listening_port = int(sys.argv[1])
    tracker_addr = sys.argv[2]
    tracker_port = int(sys.argv[3])

    difficulty = 4

    if len(sys.argv) >= 5:
        difficulty = int(sys.argv[4])
    
    vote_file = None
    if len(sys.argv) >= 6:
        vote_file = sys.argv[5]

    peer = Peer(tracker_addr, tracker_port, listening_port, difficulty, vote_file, debug=True)
    peer.send_join_message()

    number_of_options = 5
    option_str = "Pick an option:\n 1. Create poll\n 2. Display available polls 3. Vote for a poll\n 4. See poll results\n 5. Quit\n"

    # we can shift this while loop to the application layer, but place it here for now
    while True:
        selected_option_str = input(option_str)

        # Enter 1/2/3/4
        if not isinstance(selected_option_str, int):
            print("You must choose an option!")
            continue

        selected_option = int(selected_option_str)

        if selected_option < 1 and selected_option > number_of_options:
            print("You must select one of the options!")
            continue

        if selected_option == 1: # Create a poll
            poll_name = input("Enter poll name")
            existing_poll = find_poll(peer, poll_name, False)

            if existing_poll:
                print("Poll name already exists!")
                continue

            num_poll_options_str = input("How many poll options do you want?")

            while True:
                valid_poll = True
                if not isinstance(num_poll_options_str, int):
                    valid_poll = False
                
                tmp = int(num_poll_options_str)
                if tmp < 2: # num_polls must be greater than 2. If not there will nothing to vote for (duh)
                    valid_poll = False
                
                if not valid_poll:
                    print("Enter a valid number!")
                    num_poll_options_str = input("How many poll options do you want?")
                    continue
    
                break

            num_poll_options = int(num_poll_options_str)

            # Collect the poll options
            poll_options = []

            while len(poll_options) < num_poll_options:
                option = input("Enter poll option: ")
                if option in poll_options:
                    print("This option has alreayd been added, add another option!")
                    continue
                poll_options.append(option)

            create_poll(peer, poll_name, poll_options)

        elif selected_option == 2: # Display all available polls
            all_polls = get_all_polls(peer)
            if len(all_polls) == 0:
                print("No available polls right now")
                continue

            for poll in all_polls:
                print(poll)
 
        elif selected_option == 3: # Vote for a particular poll
            poll_name = input("Which poll do you want to vote for? ")
            existing_poll = find_poll(peer, poll_name, False)
            if not existing_poll:
                print(f"Poll {poll_name} does not exist!")
                continue

            poll_options = existing_poll["options"]
            print(f"Here are the available options for {poll_name}:")
            for i in range(len(poll_options)):
                print(f"{i + 1}: {poll_options[i]}")
            selected_option_str = input("Which option do you want to vote for? ")

            if not isinstance(selected_option_str, int):
                print("Enter a valid number!")
                continue

            selected_option = int(selected_option_str)

            if selected_option < 1 or selected_option > len(poll_options):
                print("Enter a valid number!")
                continue

            vote(peer, existing_poll["poll_id"], selected_option)
            # create a transaction for this vote
        elif selected_option == 4: # Display results for a poll
            poll_name = input("Which poll do you want to see? ")
            existing_poll = find_poll(peer, poll_name, False)
            if not existing_poll:
                print(f"Poll {poll_name} does not exist!")
                continue
            
            poll_results = get_poll_results(peer, existing_poll["poll_id"]) # we can probably get a nice formatter to print the results
            print(poll_results)

        elif selected_option == 5: # Quit, handle closing logic outside while loop
            break        

    print("Closing...")
    ################################################################ Get blockchain test
    # print(peer.get_port_from_peer_id(peer.public_key_to_bytes()))
    # dumb_chain = Blockchain()
    
    # transaction = Transaction(
    #     sender = peer.public_key_to_bytes(),
    #     timestamp= time.time(),
    #     data = "dummy"
    # )
    # transaction.sign(peer.private_key)

    # dummy_block = Block(_id=0, txns=[transaction], nonce=100, prev_hash=2, _hash=1)
    # dumb_chain.add_block(dummy_block)
    # peer.blockchain = dumb_chain 
    # dumb_network_chain = peer.get_chain_from_peer('127.0.0.1', peer.public_key_to_bytes())
    # print(dumb_network_chain.get_latest_block())
    # print(dumb_network_chain.get_latest_block().id)

    ############################################################################

    # serialized_nodes = peer.request_nodes_from_tracker()
    # nodes = peer.parse_serialized_nodes(serialized_nodes)
    # print(nodes)

    # dummy_block = Block(_id=1, data="dummy", nonce=100, prev_hash=2, _hash=1)
    # peer.broadcast_block_to_all_peers(dummy_block)
    # peer.request_block_from_all_peers(nodes, 100)