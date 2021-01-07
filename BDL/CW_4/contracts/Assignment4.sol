pragma solidity >=0.4.22 <0.8.0;

import "./IERCiobToken.sol";
import "./IERCiobReceiver.sol";
import "./SafeMath.sol";

contract FairSwap is IERCiobReceiver {
    using SafeMath for uint256;

    struct TokenContract{
        IERCiobToken C;
        address contractAddress;
    }

    struct Participant {
        address id;
        uint256 nrTokens;
        bool paid;
    }

    mapping (address => uint256) lastActivity;
    mapping (address => uint256) accepterTokenBalance;
    mapping (address => uint256) initiatorTokenBalance;

    Participant initiator;
    Participant accepter;

    uint256 initiateBlock;
    uint256 initiateLockTime;

    uint256 acceptBlock;
    uint256 acceptLockTime;

    bool initiatorPaid;
    bool accepterPaid;

    TokenContract public initiatorToken;
    TokenContract public accepterToken;

    address private owner;
    constructor(address initiatorTokenAddress, address accepterTokenAddress) {
        owner = msg.sender;

        initiatorToken.C = IERCiobToken(initiatorTokenAddress);
        initiatorToken.contractAddress = initiatorTokenAddress;

        accepterToken.C = IERCiobToken(accepterTokenAddress);
        accepterToken.contractAddress = accepterTokenAddress;

        initiateLockTime = 50; //10 minutes roughly -> decrease for testing; no one else can initiate contract;
        acceptLockTime = 50; //no one can initiate contract; no one can accept contract; perhaps rename it.
    }

    function getInitiatorContractAddress() external view returns (address) {
        return initiatorToken.contractAddress;
    }

    function getAccepterContractAddress() external view returns (address) {
        return accepterToken.contractAddress;
    }

    // Can restrict: initiator must have tokens from first contract, makes things easier, saves gas.
    // It is assumed that participants know which contracts are allowed. Each specify the contract they have tokens on.
    function initiateSwap(uint256 initiatorTokens, address tokenAddress, address accepterAddress, uint256 requestedTokens) external {
        // tokenAddress = acts as a confirmation that the initiator is aware of which contract he has tokens on;

        require(initiatorToken.contractAddress == tokenAddress, "Incorrect initiator token address.");
        require(block.number - initiateBlock > initiateLockTime, "Another swap is currently in progress.");
        require(block.number - acceptBlock > acceptLockTime, "Another swap is currently in progress.");

        initiator.id = msg.sender;
        initiator.nrTokens = initiatorTokens;

        accepter.id = accepterAddress;
        accepter.nrTokens = requestedTokens;

        initiateBlock = block.number;
        //Emit an event perhaps.
    }

    function acceptSwap(uint256 nrTokens, address tokenAddress, address initiatorAddress, uint256 requestedTokens) external {
        // Can call accept swap if initiated is true.
        // If accepted is false.
        // That's all, match; if everything checks out COOL + set shit.
        require(accepterToken.contractAddress == tokenAddress, "Incorrect accepter token address."); // This could be safely removed. Same above.
        require(block.number - initiateBlock <= initiateLockTime, "Late accept.");
        require(block.number - acceptBlock > acceptLockTime, "Another swap is currently in progress.");

        require(nrTokens == accepter.nrTokens, "Swap details mismatch: accepter.nrTokens");
        require(requestedTokens == initiator.nrTokens, "Swap details mismatch: initiator.nrTokens");
        require(initiatorAddress == initiator.id, "Swap details mismatch: initiator identity");
        require(msg.sender == accepter.id, "Swap details mismatch: accepter identity");

        acceptBlock = block.number;
        // Perhaps emit an event that swap has begun.
        lastActivity[accepter.id] = block.number;
        lastActivity[initiator.id] = block.number;
    }

    function receiveERCiobTokens(address sender, uint amount) public override {
        // Need to make sure that msg sender is one of two contracts.
        // Need to make sure that sender is one of two participants.
        // Need to make sure that the amounts are correct.
        // If both paid, resolve it and reset contract state.
        // Need to make sure that initiated and accepted are true.
        // Paid [msg.sender] must be false.
        require(block.number - acceptBlock <= acceptLockTime, "Funds sent too late.");
        
        bool isInitiator = msg.sender == initiatorToken.contractAddress;
        bool isAccepter = msg.sender == accepterToken.contractAddress;
        require(isInitiator || isAccepter, "Unrecognised sender contract.");

        if (isInitiator) {
            require(sender == initiator.id, "Unrecognised sender.");
            require(amount == initiator.nrTokens, "Insufficient number of tokens");

            if(accepter.paid) {
                initiatorToken.C.transfer(accepter.id, initiator.nrTokens);
                accepterToken.C.transfer(initiator.id, accepter.nrTokens);

                // Emit an event probably.
                // Is it necessary to require that these functions return true?.
                // Now, reset contract state.
                accepterTokenBalance[accepter.id].sub(accepter.nrTokens);

                initiator.id = address(0);
                initiator.nrTokens = 0;
                initiator.paid = false;

                accepter.id = address(0);
                accepter.nrTokens = 0;
                accepter.paid = false;

                initiateBlock = 0;
                acceptBlock = 0;
            }

            else {
                initiatorTokenBalance[initiator.id].add(initiator.nrTokens);
                initiator.paid = true;
                // Perhaps update last activity? Unsure. When do we update it?
            }

        }
        else {
            require(sender == accepter.id, "Unrecognised sender");
            require(amount == accepter.nrTokens, "Insufficient number of tokens");


            if(initiator.paid) {
                initiatorToken.C.transfer(accepter.id, initiator.nrTokens);
                accepterToken.C.transfer(initiator.id, accepter.nrTokens);

                initiatorTokenBalance[initiator.id].sub(initiator.nrTokens);

                initiator.id = address(0);
                initiator.nrTokens = 0;
                initiator.paid = false;

                accepter.id = address(0);
                accepter.nrTokens = 0;
                accepter.paid = false;

                initiateBlock = 0;
                acceptBlock = 0;
            }

            else {
                accepterTokenBalance[accepter.id].add(accepter.nrTokens);
                accepter.paid = true;
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