pragma solidity >=0.4.22 <0.8.0;

import "./IERCiobToken.sol";
import "./IERCiobReceiver.sol";
import "./SafeMath.sol";

contract FairSwap is IERCiobReceiver {
    using SafeMath for uint256;

    address public tokenInit;
    address public tokenAccept;

    address initiator;
    uint256 initiatorStake;

    address accepter;
    uint256 accepterStake;

    mapping (address => uint256) acceptTokenBalance;
    mapping (address => uint256) initTokenBalance;

    uint256 lockTime;
    uint256 initiateBlock;

    address private owner;

    constructor(address initContract, address acceptContract) public {
        owner = msg.sender;

        tokenInit = initContract;
        tokenAccept = acceptContract;

        lockTime = 5;
    }

    function receiveERCiobTokens(address sender, uint amount) public override {
        bool isInitiator = msg.sender == tokenInit;
        bool isAccepter = msg.sender == tokenAccept;
        require(isInitiator || isAccepter, "Unrecognised sender contract.");

        if (isInitiator) {
            initTokenBalance[sender].add(amount);
        }
        else {
            acceptTokenBalance[sender].add(amount);
        }
    }

    function initiateSwap(uint256 tokens, address swapPartner, uint256 partnerTokens) external {
        require(block.number - initiateBlock > lockTime, "Another swap is currently in progress.");
        require(initTokenBalance[msg.sender] >= tokens, "Insufficient funds.");

        initiator = msg.sender;
        initiatorStake = tokens;
        accepter = swapPartner;
        accepterStake = partnerTokens;

        initiateBlock = block.number;
        // Probably emit an event.
    }

    function acceptSwap(uint256 tokens, address swapPartner, uint256 partnerTokens) external {
        require(block.number - initiateBlock <= lockTime, "Late accept.");

        if(tokens == accepterStake && swapPartner == initiator && msg.sender == accepter && partnerTokens == initiatorStake) {
            require(acceptTokenBalance[msg.sender] >= tokens, "Insufficient funds to accept the swap.");

            IERCiobToken initContract = IERCiobToken(tokenInit);
            IERCiobToken acceptContract = IERCiobToken(tokenAccept);

            initTokenBalance[initiator].sub(initiatorStake);
            acceptTokenBalance[msg.sender].sub(tokens);

            initContract.transfer(accepter, initiatorStake);
            acceptContract.transfer(initiator, accepterStake);

            initiateBlock = 0;
        }
        else {
            revert("Swap details mismatch");
        }
    }

    function withdrawTokens(address tokenAddress) external {
        if(msg.sender == initiator) {
            require(block.number - initiateBlock > lockTime, "You have committed to a swap. Cannot withdraw at this time");
        }

        if(tokenAddress == tokenInit) {
            uint256 balance = initTokenBalance[msg.sender];
            initTokenBalance[msg.sender].sub(balance);

            IERCiobToken token = IERCiobToken(tokenInit);
            token.transfer(msg.sender, balance);
        }

        if(tokenAddress == tokenAccept) {
            uint256 balance = acceptTokenBalance[msg.sender];
            acceptTokenBalance[msg.sender].sub(balance);

            IERCiobToken token = IERCiobToken(tokenAccept);
            token.transfer(msg.sender, balance);
        }

        revert("Unrecognised token contract.");
    }
}