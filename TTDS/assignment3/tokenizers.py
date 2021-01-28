import re
from typing import List

class Tokenizer():
    def __init__(self):
        pass

    def tokenize_text_lines(self, text_lines:List[str]) -> List[str]:
        pass

    def tokenize_string(self, string:str) -> List[str]:
        pass

class RegexpTokenizer():
    def __init__(self, pattern:str):
        super().__init__()
        self.regexp = re.compile(pattern, re.MULTILINE | re.DOTALL)
    
    def tokenize_text_lines(self, text_lines:List[str]) -> List[str]:
        tokens = []
        for line in text_lines:
            tokens += self.tokenize_string(line)
        return tokens

    def tokenize_string(self, string:str) -> List[str]:
        tokens = self.regexp.findall(string)
        return tokens