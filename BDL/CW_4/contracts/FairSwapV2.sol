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
        require(initContract != acceptContract, "C1 and C2 must differ");

        tokenInit = initContract;
        tokenAccept = acceptContract;

        lockTime = 50;
        
        initiator = msg.sender;
        initiatorStake = 1;
        accepter = msg.sender;
        accepterStake = 1;
        initiateBlock = 1;
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
        require(block.number.sub(initiateBlock) > lockTime, "Another swap is currently in progress.");

        initiator = msg.sender;
        initiatorStake = tokens;
        accepter = swapPartner;
        accepterStake = partnerTokens;

        initiateBlock = block.number;
        emit SwapInitiated(initiator, accepter, initiatorStake, accepterStake);
    }

    function acceptSwap(uint256 tokens, address swapPartner, uint256 partnerTokens) external {
        require(block.number.sub(initiateBlock) <= lockTime, "Late accept or swap has finished.");

        if(tokens == accepterStake && swapPartner == initiator && msg.sender == accepter && partnerTokens == initiatorStake) {

            initTokenBalance[initiator] = initTokenBalance[initiator].sub(initiatorStake);
            acceptTokenBalance[accepter] = acceptTokenBalance[accepter].sub(accepterStake);
            initTokenBalance[accepter] = initTokenBalance[accepter].add(initiatorStake);
            acceptTokenBalance[initiator] = acceptTokenBalance[initiator].add(accepterStake);

            initiateBlock = 1;

            emit SwapFinished(initiator, accepter, initiatorStake, accepterStake);
        }
        else {
            revert("Swap details mismatch");
        }
    }

    function withdrawTokens(address tokenAddress) external {
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