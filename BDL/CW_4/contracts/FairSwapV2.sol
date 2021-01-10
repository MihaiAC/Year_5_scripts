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

    event SwapInitiated(address initiator, address accepter, uint256 initiatorStake, uint256 accepterStake);
    event SwapFinished(address initiator, address accepter, uint256 initiatorStake, uint256 accepterStake);

    constructor(address initContract, address acceptContract) public {
        tokenInit = initContract;
        tokenAccept = acceptContract;

        lockTime = 5;
    }

    function receiveERCiobTokens(address sender, uint amount) public override {
        bool isInitiator = msg.sender == tokenInit;
        bool isAccepter = msg.sender == tokenAccept;
        require(isInitiator || isAccepter, "Unrecognised sender contract.");

        if (isInitiator) {
            initTokenBalance[sender] = initTokenBalance[sender].add(amount);
        }
        else {
            acceptTokenBalance[sender] = acceptTokenBalance[sender].add(amount);
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
        emit SwapInitiated(initiator, accepter, initiatorStake, accepterStake);
    }

    function acceptSwap(uint256 tokens, address swapPartner, uint256 partnerTokens) external {
        require(block.number - initiateBlock <= lockTime, "Late accept.");

        if(tokens == accepterStake && swapPartner == initiator && msg.sender == accepter && partnerTokens == initiatorStake) {
            require(acceptTokenBalance[msg.sender] >= tokens, "Insufficient funds to accept the swap.");

            IERCiobToken initContract = IERCiobToken(tokenInit);
            IERCiobToken acceptContract = IERCiobToken(tokenAccept);

            initTokenBalance[initiator] = initTokenBalance[initiator].sub(initiatorStake);
            acceptTokenBalance[accepter] = acceptTokenBalance[accepter].sub(accepterStake);

            initiateBlock = 0; // Potential hazard: double swap by accepter. This is against that. Could also make initiator 0x?

            initContract.transfer(accepter, initiatorStake);
            acceptContract.transfer(initiator, accepterStake);

            emit SwapFinished(initiator, accepter, initiatorStake, accepterStake);
        }
        else {
            revert("Swap details mismatch");
        }
    }

    function withdrawTokens(address tokenAddress) external {
        if(msg.sender == initiator && tokenAddress == tokenInit) {
            require(block.number - initiateBlock > lockTime, "You have committed to a swap. Cannot withdraw at this time");
        }

        if(tokenAddress == tokenInit) {
            uint256 balance = initTokenBalance[msg.sender];
            initTokenBalance[msg.sender] = initTokenBalance[msg.sender].sub(balance);

            IERCiobToken token = IERCiobToken(tokenInit);
            token.transfer(msg.sender, balance);
        }
        else if(tokenAddress == tokenAccept) {
            uint256 balance = acceptTokenBalance[msg.sender];
            acceptTokenBalance[msg.sender] = acceptTokenBalance[msg.sender].sub(balance);

            IERCiobToken token = IERCiobToken(tokenAccept);
            token.transfer(msg.sender, balance);
        }
        else {
            revert("Unrecognised token contract.");
        }
    }
}