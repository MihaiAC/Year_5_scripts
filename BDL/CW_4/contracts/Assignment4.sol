pragma solidity >=0.4.22 <0.8.0;

import "./IERCiobToken.sol";
import "./IERCiobReceiver.sol";
import "./SafeMath.sol";

contract FairSwap is IERCiobReceiver {
    using SafeMath for uint256;

    mapping (address => uint256) lastActivity;
    mapping (address => uint256) accepterTokenBalance;
    mapping (address => uint256) initiatorTokenBalance;

    address initiator;
    address accepter;
    uint256 initiatorStake;
    uint256 accepterStake;

    uint256 initiateBlock;
    uint256 initiateLockTime;

    uint256 acceptBlock;
    uint256 acceptLockTime;

    bool initiatorPaid;
    bool accepterPaid;

    address public initToken;
    address public acceptToken;

    address private owner;
    constructor(address initiatorTokenAddress, address accepterTokenAddress) public {
        owner = msg.sender;

       initToken = initiatorTokenAddress;
       acceptToken = accepterTokenAddress;

        initiateLockTime = 5; //10 minutes roughly -> decrease for testing; no one else can initiate contract;
        acceptLockTime = 5; //no one can initiate contract; no one can accept contract; perhaps rename it.
    }

    function initiateSwap(uint256 initiatorTokens, address accepterAddress, uint256 requestedTokens) external {
        require(block.number - initiateBlock > initiateLockTime, "Another swap is currently in progress.");
        require(block.number - acceptBlock > acceptLockTime, "Another swap is currently in progress.");

        initiator = msg.sender;
        initiatorStake = initiatorTokens;

        accepter = accepterAddress;
        accepterStake = requestedTokens;

        initiateBlock = block.number;
        //Emit an event perhaps.
    }

    function acceptSwap(uint256 nrTokens, address initiatorAddress, uint256 requestedTokens) external {
        require(block.number - initiateBlock <= initiateLockTime, "Late accept.");
        require(block.number - acceptBlock > acceptLockTime, "Another swap is currently in progress.");

        if(nrTokens == accepterStake && requestedTokens == initiatorStake && msg.sender == accepter && initiatorAddress == initiator) {
            acceptBlock = block.number;
            
            lastActivity[accepter] = block.number;
            lastActivity[initiator] = block.number;
        }
        else {
            revert("Swap details mismatch.");
        }
    }
    
    function receiveERCiobTokens(address sender, uint amount) public override {
        // Need to make sure that msg sender is one of two contracts.
        // Need to make sure that sender is one of two participants.
        // Need to make sure that the amounts are correct.
        // If both paid, resolve it and reset contract state.
        // Need to make sure that initiated and accepted are true.
        // Paid [msg.sender] must be false.
        require(block.number - acceptBlock <= acceptLockTime, "Funds sent too late.");
        
        bool isInitiator = msg.sender == initToken;
        bool isAccepter = msg.sender == acceptToken;
        require(isInitiator || isAccepter, "Unrecognised sender contract.");

        if (isInitiator) {
            require(sender == initiator, "Unrecognised sender.");
            require(amount == initiatorStake, "Insufficient number of tokens");

            if(accepter.paid) {
                // Emit an event probably.
                accepterTokenBalance[accepter] = accepterTokenBalance[accepter].sub(accepterStake);
                initiatorTokenBalance[accepter] = initiatorTokenBalance[accepter.id].add(initiatorStake);
                accepterTokenBalance[initiator] = accepterTokenBalance[initiator].add(accepterStake);
            }

            else {
                initiatorTokenBalance[initiator] = initiatorTokenBalance[initiator].add(initiatorStake);
                initiatorPaid = true;
            }

        }
        else {
            require(sender == accepter.id, "Unrecognised sender");
            require(amount == accepter.nrTokens, "Insufficient number of tokens");

            if(initiator.paid) {
                // Emit an event probably?
                accepterTokenBalance[initiator] = accepterTokenBalance[initiator].add(accepterStake);
                initiatorTokenBalance[accepter] = initiatorTokenBalance[accepter].add(initiatorStake);
                initiatorTokenBalance[initiator] = initiatorTokenBalance[initiator].sub(initiatorStake);
            }

            else {
                accepterTokenBalance[accepter] = accepterTokenBalance[accepter].add(accepterStake);
                accepterPaid = true;
            }
        }
    }

    function withdrawInitiatorBalance() external {
        
        require(block.number - lastActivity[msg.sender] > acceptLockTime, "Cannot withdraw yet.");
        if(initiatorTokenBalance[msg.sender] > 0) {
            uint256 balance = initiatorTokenBalance[msg.sender];
            initiatorTokenBalance[msg.sender] = 0;
            lastActivity[msg.sender] = 0;

            initiatorToken.C.transfer(msg.sender, balance); // require true?
        }
    }

    function withdrawContractBalance() external {
        require(block.number - lastActivity[msg.sender] > acceptLockTime, "Cannot withdraw yet.");
        if(accepterTokenBalance[msg.sender] > 0) {
            uint256 balance = accepterTokenBalance[msg.sender];
            accepterTokenBalance[msg.sender] = 0;
            lastActivity[msg.sender] = 0;

            accepterToken.C.transfer(msg.sender, balance); // require true?
        }
    }

    // What if none of the two call this?
    // Need onlyowner function which resets swap (ONLY FOR THIS CASE.)
    // Not necessarily. Disallow payments after the thing has passed?

    // function resetState?
    // function withdrawInitiate
    // function withdrawPayment - in case;


}