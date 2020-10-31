pragma solidity >=0.4.22 <0.7.0;

contract mc_morra {
    struct Player {
        bytes32 commit;
        bool revealed;
        uint8 guess;
        uint8 played_number;
    }
    
    mapping (address => uint256) players_balances;
    mapping (address => Player) players;
    uint256 last_commit_block;
    uint256 last_reveal_block;
    address player_1;
    address player_2;
    
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
        require(commit_hash != 0, "Cannot commit an empty hash.");
        bool p1_exists = player_1 != address(0);
        bool p2_exists = player_2 != address(0);
        require(!p1_exists || !p2_exists, "There are already two participants playing the game.");
        
        players[msg.sender].commit = commit_hash;
        last_commit_block = block.number;
        
        if (!p1_exists) {
            player_1 = msg.sender;
        }
        else {
            player_2 = msg.sender;
        }
    }
    
    function cancel_participation() external {
        require(players[msg.sender].commit != 0, "Message sender is not a participant.");
        /// If this point is reached, there is at least one committed player.
        bool p1_exists = player_1 != address(0);
        bool p2_exists = player_2 != address(0);
        require(!(p1_exists && p2_exists), "Both players have committed. Cancelling your participation is not possible at this time.");
        
        
        if (p1_exists) {
            delete player_1;
        }
        else {
            delete player_2;
        }
        
        delete players[msg.sender];
        players_balances[msg.sender] = 5 * 1e18;
        delete last_commit_block;
    }
    
    function reveal(uint8 guess, uint8 played_number, uint8 safety_number) external {
        require (msg.sender == player_1 || msg.sender == player_2, "Message sender is not a player.");
        require (players[player_1].commit != 0 && players[player_2].commit != 0, "Fewer than two committed players.");
        require (players[msg.sender].revealed == false, "You have already revealed.");
        require (uint256(block.number) > last_commit_block, "Revealed too soon!");
        require (uint256(block.number) <= last_commit_block + grace_period, "Revealed too late!");
        require (compute_hash(msg.sender, guess, played_number, safety_number)==players[msg.sender].commit, "Reveal hash does not match commit.");
        
        players[msg.sender].guess = guess;
        players[msg.sender].played_number = played_number;
        players[msg.sender].revealed = true;
        
        last_reveal_block = block.number;
    }
    
    
    function decide_winner() external {
        require(msg.sender == player_1 || msg.sender == player_2, "Message sender is not a player.");
        require(players[player_1].revealed && players[player_2].revealed, "Players have not revealed yet.");
        
        bool valid_1 = players[player_1].played_number > 0 && players[player_1].played_number <= 5;
        bool valid_2 = players[player_2].played_number > 0 && players[player_2].played_number <= 5;
        
        if (valid_1 && valid_2) {
            bool guess_1 = players[player_1].guess == players[player_2].played_number;
            bool guess_2 = players[player_2].guess == players[player_1].played_number;
            if (guess_1 && !guess_2) {
                players_balances[player_1] += 6 * 1e18 + players[player_2].played_number * 1e18;
                players_balances[player_2] += 6 * 1e18 - players[player_2].played_number * 1e18;
            }
            else if (!guess_1 && guess_2) {
                players_balances[player_1] += 6 * 1e18 - players[player_1].played_number * 1e18;
                players_balances[player_2] += 6 * 1e18 + players[player_1].played_number * 1e18;
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
    }
    
    function withdraw_balance() external {
        //Source: https://fravoll.github.io/solidity-patterns/pull_over_push.html.
        uint256 player_balance = players_balances[msg.sender];
        require (player_balance != 0, "Your balance is 0.");
        players_balances[msg.sender] = 0;
        msg.sender.transfer(player_balance);
    }
    
    function compute_hash(address player, uint8 guess, uint8 played_number, uint8 safety_number) public pure returns(bytes32) {
        return keccak256(abi.encodePacked(player, guess, played_number, safety_number));
    }
    
    //Owner-only function.
    function forcefully_end_game() external only_owner {
        require(players[player_1].commit != 0 && players[player_2].commit != 0, "Cannot end game. Fewer than two committed players.");
        bool p1_revealed = players[player_1].revealed;
        bool p2_revealed = players[player_2].revealed;
        if(!p1_revealed || !p2_revealed) {
            require(block.number > grace_period + last_commit_block, "Cannot end game until the grace period has passed.");
            if(p2_revealed) {
                players_balances[player_2] += 5 * 1e18;
            }
            else {
                players_balances[player_1] += 5 * 1e18;
            }
        }
        else {
            require(block.number > grace_period + last_reveal_block, "Cannot end game until the grace period has passed.");
        }
        
        delete players[player_1];
        delete players[player_2];
        delete player_1;
        delete player_2;
    }
    
    //Owner-only function.
    function withdraw_contract_balance() external only_owner {
        msg.sender.transfer(address(this).balance);
    }
    
    receive() external payable {
        revert();
    }
    ///Fallback function, do nothing for now.
    fallback() external payable {
        revert();
    }
}
