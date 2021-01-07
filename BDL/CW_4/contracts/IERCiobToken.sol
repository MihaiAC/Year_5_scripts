pragma solidity >=0.4.22 <0.8.0;

contract IERCiobToken {
    uint256 public tokenPrice;

    function buyToken(uint256 amount) external payable returns(bool) {}
    function transfer(address recipient, uint256 amount) external returns(bool) {}
    function sellToken(uint256 amount) external returns(bool) {}
    function changePrice(uint256 price) external payable returns(bool) {}
    function getBalance() external view returns(uint256) {}
}