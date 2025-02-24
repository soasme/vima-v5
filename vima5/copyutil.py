import json
import sys
import pyperclip
import time

def copy_strings_to_clipboard(string_array):
    """
    Copies each string in the input array to the clipboard, pausing for user input 
    before proceeding to the next string.

    Args:
        string_array: A list of strings.
    """
    if not string_array:
        print("Empty string array.")
        return

    for s in string_array:
        pyperclip.copy(s)
        print(f"String '{s}' copied to clipboard. Press Enter to copy the next string...")
        input("Press Enter to continue...")
        time.sleep(0.1) # small delay to prevent issues with rapid pasting.

# Example usage:
with open(sys.argv[1], 'r') as f:
    my_strings = json.loads(f.read())
copy_strings_to_clipboard(my_strings)
