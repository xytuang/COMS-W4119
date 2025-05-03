import sys
import uuid
import time

from enums import State
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
    chain = peer.get_chain()
    for block in chain:
        for txn in block.txns:
            txn_data = txn.data
            # print("LOG find_poll txn_data:", txn_data)
            if txn_data["transaction_type"] == "create_poll" and txn_data[poll_field] == poll_identifier:
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
    chain = peer.get_chain()
    for block in chain:
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
    
    options = poll["options"]
    options_count = {option: 0 for option in poll["options"]}

    chain = peer.get_chain()
    for block in chain:
        for txn in block.txns:
            txn_data = txn.data
            # print(txn_data)
            if txn_data["poll_id"] == poll_id and txn_data["transaction_type"] == "vote":
                voted_option = txn_data["vote"]
                # print(f"voted_option: {voted_option}")
                # print(f"Found voted option: {voted_option in options}")
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


def is_int(input_str, rng=None):
    """
    Checks if input_str can be converted to a int and is within the range specified by rng

    Args:
        input_str (str): User's input string
        rng (list): list with 2 elements, first element represents min, second element represents max
    """
    try:
        x = int(input_str)
        if rng is None:
            return True
        if x >= rng[0] and x <= rng[1]:
            return True
        return False
    except ValueError:
        return False
    
def shutdown(peer):
    """
    Shutdown procedure for a peer
    
    Args:
        peer (Peer): the peer instance to shut down
    """
    
    print("\nStarting shutdown procedure...")
    
    with peer.state_lock:
        peer.state = State.SHUTTING_DOWN
    
    peer.shutdown_event.set() # signal all threads to terminate
    
    # 1. closing tracker connection
    print("Closing connection to tracker...")
    try:
        with peer.tracker_lock:
            try:
                leave_msg = "LEAVE\n"
                peer.tracker_socket.sendall(leave_msg.encode())
            except Exception as e:
                print(f"Failed to send leave message: {e}")
            
            peer.tracker_socket.close()
    except Exception as e:
        print(f"Error closing tracker connnection: {e}")        
    
    # 2. closing listening socket
    print("Closing listenning port...")
    try:
        peer.listening_sock.close()
    except Exception as e:
        print(f"Error closing listening socket: {e}")
        
    print("Waiting for threads to finish...")
    
    timeout = 3 # avoid hanging
    # join the threads with timeout (smae for all three threads)
    if hasattr(peer, 'listening_thread') and peer.listening_thread.is_alive():
        peer.listening_thread.join(timeout)
        if peer.listening_thread.is_alive():
            print("Warning: listening thread didn't terminate properly!")
            
    if hasattr(peer, 'polling_thread') and peer.polling_thread.is_alive():
        peer.polling_thread.join(timeout)
        if peer.polling_thread.is_alive():
            print("Warning: polling thread didn't terminate properly!")

    if hasattr(peer, 'mining_thread') and peer.mining_thread.is_alive():
        peer.mining_thread.join(timeout)
        if peer.mining_thread.is_alive():
            print("Warning: mining thread didn't terminate properly!")
    
    peer.log_file.close()
    print("Peer all shut down")
    
    

def parse_sim_file(sim_file, peer):
    with open(sim_file, 'r') as f:
        for line in f:
            line_strp = line.strip()
            data_arr = line_strp.split(' ')
            if data_arr[0] == "CREATE":
                poll_name = data_arr[1]
                options = []
                for i in range(2, len(data_arr)):
                    options.append(data_arr[i])
                create_poll(peer, poll_name, options)
                print(f"Submitted transaction for creating poll with {poll_name} and options {str(options)}")
            elif data_arr[0] == "VOTE":
                poll_name = data_arr[1]
                poll = find_poll(peer, poll_name, using_id=False)
                if poll == None:
                    print("Did not find poll.")
                    continue
                option = data_arr[2]
                vote(peer, poll["poll_id"], option)
                print(f"Submitted transation for voting {option} on {poll_name}")
            elif data_arr[0] == "SLEEP":
                print(f"Sleeping for {str(data_arr[1])} s")
                time.sleep(float(data_arr[1]))
            else:
                print("Unsupported command type")

if __name__ == '__main__':
    listening_port = int(sys.argv[1])
    tracker_addr = sys.argv[2]
    tracker_port = int(sys.argv[3])

    difficulty = 4

    if len(sys.argv) >= 5:
        difficulty = int(sys.argv[4])
    
    config_file = None
    if len(sys.argv) >= 6:
        config_file = sys.argv[5]
        print(config_file)

    sim_file = None
    if len(sys.argv) >= 7:
        sim_file = sys.argv[6]

    peer = Peer(tracker_addr, tracker_port, listening_port, difficulty, debug=False)

    if config_file != None:
        peer.set_configs_from_file(config_file)

    peer.send_join_message()

    if sim_file != None:
        parse_sim_file(sim_file, peer)

    number_of_options = 5
    option_str = "Pick an option:\n 1. Create poll\n 2. Display available polls\n 3. Vote for a poll\n 4. See poll results\n 5. Quit\n"

    try:
        # we can shift this while loop to the application layer, but place it here for now
        while True:
            print("-------------------------------------------")
            selected_option_str = input(option_str)

            if not is_int(selected_option_str, [1, number_of_options]):
                print("You must provide a valid integer!")
                continue

            selected_option = int(selected_option_str)

            if selected_option == 1: # Create a poll
                poll_name = input("Enter poll name: ")
                existing_poll = find_poll(peer, poll_name, False)

                if existing_poll:
                    print("Poll name already exists!")
                    continue

                num_poll_options_str = input("How many poll options do you want? ")

                while True:
                    if not is_int(num_poll_options_str, [2, float("inf")]): # num_polls must be at least  2. If not there will nothing to vote for (duh)
                        print("Enter a valid number!")
                        num_poll_options_str = input("How many poll options do you want? ")
                        continue

                    break

                num_poll_options = int(num_poll_options_str)

                # Collect the poll options
                poll_options = []

                while len(poll_options) < num_poll_options:
                    option = input("Enter poll option: ")
                    if option in poll_options:
                        print("This option has already been added, add another option!")
                        continue
                    poll_options.append(option)

                create_poll(peer, poll_name, poll_options)

            elif selected_option == 2: # Display all available polls
                all_polls = get_all_polls(peer)
                if len(all_polls) == 0:
                    print("No available polls right now")
                    continue

                for poll in all_polls:
                    poll_name = poll["poll_name"]
                    options = poll["options"]

                    print(f"Poll name: {poll_name}")
                    print(f"Options: {options}\n")
    
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

                if selected_option_str not in existing_poll["options"]:
                    print("Enter a valid option!")
                    continue

                vote(peer, existing_poll["poll_id"], selected_option_str)
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
                print("Start shutting down...")
                shutdown(peer)
                break
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        try:
            shutdown(peer)
        except:
            print("Error shutting down after exception")
        raise

    print("Closed successfully")
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