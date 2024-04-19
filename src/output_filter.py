import re

def strip_enclosing_chars(input_str:str, enclosing_chars:str) -> str:
    """
    Remove and enclosing characters
    """

    if len(input_str) < 2:
        return input_str
    if input_str[0] == input_str[-1] and input_str[0] in enclosing_chars:
        print("Removing an enclosing character from: " + input_str)
        return strip_enclosing_chars(input_str[1:-1], enclosing_chars)
    return input_str

def command_output_cleaner(input_str:str) -> str:
    """
    Cleans up the command output to make it more usable from the LLM
    """

    input_str = input_str.strip(" \n")
    if len(input_str) < 2:
        return input_str

    pattern = re.compile(r"^[ \n\r]*```.*\n(.*)\n```$", re.MULTILINE)
    match = pattern.search(input_str)
    if match:
        print("Matched with the multi-line regex 1")
        input_str = match.group(1)
        print("Updated command: " + input_str)
    pattern = re.compile(r"^[ \n\r]*~~~.*\n(.*)\n~~~$", re.MULTILINE)
    match = pattern.search(input_str)
    if match:
        print("Matched with the multi-line regex 2")
        input_str = match.group(1)
        print("Updated command: " + input_str)
    pattern = re.compile(r"^[ \n\r]*~~~.*\n(.*)\n~~~$", re.MULTILINE)

    input_str = strip_enclosing_chars(input_str, "`'\"")

    if input_str.startswith("$ "):
        input_str = input_str[2:]
    
    return input_str