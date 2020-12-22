pragma solidity >=0.4.22 <0.8.0;

import SafeMath from "./SafeMath.sol"
import IERCiobReceiver from "./IERCiobToken.sol"

contract ERCiobToken {
    using SafeMath for uint256;

    address public owner;

    uint256 public tokenPrice;
    uint256 private nrSoldTokens;
    mapping (address => uint256) owned_tokens;
    uint8 timeout_period;
    uint256 public last_price_change_block;


    event Purchase(address buyer, uint256 amount);
    event Transfer(address sender, address receiver, uint256 amount);
    event Sell(address seller, uint256 amount);
    event Price(uint256 price);

    constructor() public {
        owner = msg.sender;
        tokenPrice = 5e14;
        timeout_period = 5;

        emit Price(tokenPrice);
    }

    function buyToken(uint256 amount) external payable returns(bool) {
        // Potential hazard: if buyer overflows amount... this is why SafeMath is used.
        require(msg.value == amount.mul(tokenPrice), "Not enough funds.");
        
        owned_tokens[msg.sender].add(amount);
        emit Purchase(msg.sender, amount);
        return true;
    }

    // Need to somehow restrict this...instead of having a timeout period, you can assume that a sender is a 
    // contract and call one of its functions to approve the transfer? (can state as an alternative)
    // Can user send tokens to 0x0? Yes, why not.
    function transfer(address recipient, uint256 amount) external returns(bool) {
        require(block.number.sub(last_price_change_block) > timeout_period, "Not enough ");

        owned_tokens[msg.sender].sub(amount);
        owned_tokens[recipient].add(amount);

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
        owned_tokens[msg.sender].sub(amount);
        msg.sender.transfer(amount.mul(tokenPrice));

        emit Sell(msg.sender, amount);
        return true;
    }

    function changePrice(uint256 price) external payable returns(bool) {
        // Only the owner can call this method.
        require(msg.sender == owner, "Only the owner can call this function.");
        require(price >= tokenPrice.mul(2), "New token price is too low to warrant a change.");
        require(address(this).balance.add(msg.value) > price.mul(nrSoldTokens), "Funds must suffice for the price increase.");

        tokenPrice = price;
        last_price_change_block = block.number;

        emit Price(price);
        return true;
    }

    function getBalance() public returns(uint256) {
        return owned_tokens[msg.sender];
    }

    
}