pragma solidity ^0.7.0;

contract HelloWorld {
    function sayHello() public pure returns(string memory){
        string memory a = "Hello World";
        return a;
    }
}