pragma solidity >=0.4.22 <0.7.0;

contract mc_morra {
    struct Player {
        bytes32 commit;
        bool committed;
        bool revealed;
        uint8 guess;
        uint8 played_number;
        uint256 commit_block;
        uint256 _balance;
        uint256 reveal_block;
    }
    
    mapping (address => uint256) players_balances;
    mapping (address => Player) players;
    address player_1;
    address player_2;
    uint8 nr_committed_players;
    uint8 nr_revealed_players;
    
    address owner;
    uint constant grace_period = 25;
    
    constructor() public {
        owner = msg.sender;
    }
    
    modifier only_owner() {
        require(msg.sender == owner);
        _;
    }
    
    function commit(bytes32 commit_hash) external payable {
        require(msg.value == 6 ether, "Commit call should include exactly 6 ETH.");
        require(nr_committed_players < 2, "There are already two participants playing the game.");
        
        players[msg.sender].commit = commit_hash;
        players[msg.sender].committed = true;
        players[msg.sender]._balance = msg.value;
        players[msg.sender].commit_block = block.number;
        
        if (nr_committed_players == 0) {
            player_1 = msg.sender;
        }
        else {
            player_2 = msg.sender;
        }
        
        nr_committed_players += 1;
        ///game_state = true;
    }
    
    // The deposit will be retained by the contract.
    function cancel_participation() external {
        require(nr_committed_players == 1, "Cancelling is not allowed at this point in time.");
        require(players[msg.sender].committed == true, "Message sender has not committed yet.");
        
        if (player_1 == msg.sender) {
            delete player_1;
        }
        else {
            delete player_2;
        }
        
        delete players[msg.sender];
        nr_committed_players -= 1;
        players_balances[msg.sender] = 5 * 1e18;
    }
    
    function reveal(uint8 guess, uint8 played_number, bytes32 safety_string) external {
        require(msg.sender == player_1 || msg.sender == player_2, "Message sender is not a player.");
        require (nr_committed_players == 2, "Fewer than two players have committed, cannot reveal.");
        require (players[msg.sender].committed == true, "Message sender is not a participant.");
        require (players[msg.sender].revealed == false, "Message sender has already tried to reveal.");
        require (uint256(block.number)>players[msg.sender].commit_block, "Cannot commit and reveal on the same block.");
        require (uint256(block.number)<=players[msg.sender].commit_block + grace_period, "Late reveal request.");
        require (compute_hash(msg.sender, guess, played_number, safety_string)==players[msg.sender].commit, "Reveal hash does not match commit.");
        
        players[msg.sender].revealed = true;
        players[msg.sender].guess = guess;
        players[msg.sender].played_number = played_number;
        players[msg.sender].reveal_block = block.number;
        nr_revealed_players += 1;
    }
    
    /// Assumption: both players have committed in time.
    function decide_winner() external {
        require(msg.sender == player_1 || msg.sender == player_2, "Message sender is not a player.");
        require(nr_revealed_players == 2, "Players have not revealed yet.");
        
        bool valid_1 = players[player_1].played_number > 0 && players[player_1].played_number <= 5;
        bool valid_2 = players[player_2].played_number > 0 && players[player_2].played_number <= 5;
        
        if (valid_1 && valid_2) {
            bool guess_1 = players[player_1].guess == players[player_2].played_number;
            bool guess_2 = players[player_2].guess == players[player_1].played_number;
            if (guess_1 && !guess_2) {
                players_balances[player_1] += players[player_1]._balance + players[player_2].played_number * 1e18;
                players_balances[player_2] += players[player_2]._balance - players[player_2].played_number * 1e18;
            }
            else if (!guess_1 && guess_2) {
                players_balances[player_1] += players[player_1]._balance - players[player_1].played_number * 1e18;
                players_balances[player_2] += players[player_2]._balance + players[player_1].played_number * 1e18;
            }
        }
        else if (valid_1) {
            players_balances[player_1] += 5 * 1e18;
        }
        else if (valid_2) {
            players_balances[player_2] += 5 * 1e18;
        }
        
        delete players[player_1];
        delete players[player_2];
        delete player_1;
        delete player_2;
        delete nr_committed_players;
        delete nr_revealed_players;
    }
    
    function withdraw_balance() external {
        //Source: https://fravoll.github.io/solidity-patterns/pull_over_push.html.
        uint256 player_balance = players_balances[msg.sender];
        
        require (player_balance != 0, "Your balance is 0.");
        players_balances[msg.sender] = 0;
        msg.sender.transfer(player_balance);
    }
    
    //Taken from: https://solidity.readthedocs.io/en/v0.4.24/contracts.html.
    function max(uint256 a, uint256 b) private pure returns(uint256) {
        return a > b ? a : b;
    }
    
    function forcefully_end_game() external only_owner {
        require(nr_committed_players == 2, "Cannot end game if there are less than 2 committed players.");
        if(nr_revealed_players < 2) {
            uint256 max_commit_block = max(players[player_1].commit_block, players[player_2].commit_block);
            require(block.number > grace_period + max_commit_block, "Cannot end game until the grace period has passed.");
            if(players[player_1].revealed == false) {
                players_balances[player_2] += 5 * 1e18;
            }
            else {
                players_balances[player_1] += 5 * 1e18;
            }
        }
        else {
            uint256 max_reveal_block = max(players[player_1].reveal_block, players[player_2].reveal_block);
            require(block.number > grace_period + max_reveal_block, "Cannot end game until the grace period has passed.");
        }
        delete players[player_1];
        delete players[player_2];
        delete player_1;
        delete player_2;
        delete nr_committed_players;
        delete nr_revealed_players;
    }
    
    function withdraw_contract_balance() external only_owner {
        msg.sender.transfer(address(this).balance);
    }
    
    function compute_hash(address player, uint8 guess, uint8 played_number, bytes32 safety_string) private pure returns(bytes32) {
        return keccak256(abi.encodePacked(player, guess, played_number, safety_string));
    }
    
    receive() external payable {
        revert();
    }
    ///Fallback function, do nothing for now.
    fallback() external payable {
        revert();
    }
}
