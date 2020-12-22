pragma solidity >=0.4.22 <0.7.0;

contract Assignment {
    address public owner;
    string private key = "this-is-the-key";
    string[] public students;

    event Registration(string);

    constructor(string memory k) public {
        owner = msg.sender;
        key = k;
    }

    function updateSeed(string memory k) public {
        require(msg.sender == owner);
        key = k;
    }

    function register(string memory k, string memory uun) public {
        require(keccak256(abi.encodePacked(k)) == keccak256(abi.encodePacked(key)));
        students.push(uun);
        emit Registration(uun);
    }
}