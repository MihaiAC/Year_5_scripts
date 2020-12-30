pragma solidity >=0.4.22 <0.8.0;

import "./SafeMath.sol";
import "./IERCiobReceiver.sol";

contract ERCiobToken {
    using SafeMath for uint256;

    uint256 public transfer_timeout_period;
    uint256 public tokenPrice;
    uint256 public nrSoldTokens;
    uint256 public last_price_change_block;
    
    address public owner;
    mapping (address => uint256) owned_tokens;
    
    event Purchase(address buyer, uint256 amount);
    event Transfer(address sender, address receiver, uint256 amount);
    event Sell(address seller, uint256 amount);
    event Price(uint256 price);

    constructor() public {
        owner = msg.sender;
        tokenPrice = 5e14;
        transfer_timeout_period = 25;
        nrSoldTokens = 1;

        emit Price(tokenPrice);
    }

    function buyToken(uint256 amount) external payable returns(bool) {
        // Potential hazard: if buyer overflows amount... this is why SafeMath is used.
        require(msg.value == amount.mul(tokenPrice), "Provided funds must exactly match the price of the bought tokens.");
        
        owned_tokens[msg.sender] = owned_tokens[msg.sender].add(amount);
        nrSoldTokens = nrSoldTokens.add(amount);

        emit Purchase(msg.sender, amount);
        return true;
    }

    // Can user send tokens to 0x0? Yes, why not.
    function transfer(address recipient, uint256 amount) external returns(bool) {
        require(block.number.sub(last_price_change_block) > transfer_timeout_period, "Token price has recently changed.");

        owned_tokens[msg.sender] = owned_tokens[msg.sender].sub(amount);
        owned_tokens[recipient] = owned_tokens[recipient].add(amount);

        // Taken from OpenZeppelin's "Address" contract.
        uint256 size;
        assembly { size:= extcodesize(recipient)}
        if(size > 0) {
            IERCiobReceiver receiver = IERCiobReceiver(recipient);
            receiver.receiveERCiobTokens(msg.sender, amount);
        }

        emit Transfer(msg.sender, recipient, amount);
        return true;
    }

    function sellToken(uint256 amount) external returns(bool) {
        owned_tokens[msg.sender] = owned_tokens[msg.sender].sub(amount);
        nrSoldTokens = nrSoldTokens.sub(amount);

        msg.sender.transfer(amount.mul(tokenPrice));

        emit Sell(msg.sender, amount);
        return true;
    }

    function changePrice(uint256 price) external payable returns(bool) {
        require(msg.sender == owner, "Only the owner can call this function.");
        require(price >= tokenPrice.mul(2), "New token price is too low to warrant a change.");
        
        uint256 contract_funds = address(this).balance;
        uint256 tokens_value = price.mul(nrSoldTokens.sub(1));

        require(contract_funds >= tokens_value, "Contract funds must cover the price increase.");

        tokenPrice = price;
        last_price_change_block = block.number;

        if(contract_funds > tokens_value) {
            msg.sender.transfer(contract_funds.sub(tokens_value));
        }

        emit Price(price);
        return true;
    }

    function getBalance() external view returns(uint256) {
        return owned_tokens[msg.sender];
    }
}