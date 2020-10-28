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
    
    mapping (address => Player) players;
    uint8 nr_committed_players;
    uint8 nr_revealed_players;
    
    address winner;

    address owner;
    bool game_state;
    uint256 game_start_block;
    uint constant grace_period = 100;
    
    constructor() public {
        owner = msg.sender;
        game_state=false;
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
        nr_committed_players = nr_committed_players + 1;
        game_state = true;
    }
    
    function reveal(uint8 guess, uint8 played_number, bytes32 safety_string) external {
        require (nr_committed_players == 2, "Fewer than two players have committed, cannot reveal.");
        require (players[msg.sender].committed == true, "Message sender is not a participant.");
        require (players[msg.sender].revealed == false, "Message sender has already tried to reveal.");
        require (uint256(block.number)>players[msg.sender].commit_block, "Commit and reveal happened on the same block.");
        require (uint256(block.number)<=players[msg.sender].commit_block + grace_period, "Late reveal request.");
        require (compute_hash(msg.sender, guess, played_number, safety_string)==players[msg.sender].commit, "Reveal hash does not match commit.");
        
        players[msg.sender].revealed = true;
        players[msg.sender].guess = guess;
        players[msg.sender].played_number = played_number;
        players[msg.sender].reveal_block = block.number;
    }
    
    function call_winner
    
    function compute_hash(address player, uint8 guess, uint8 played_number, bytes32 safety_string) private pure returns(bytes32) {
        return keccak256(abi.encodePacked(player, guess, played_number, safety_string));
    }
    
    ///Fallback function, do nothing for now.
    fallback() external payable {
        revert();
    }
}
