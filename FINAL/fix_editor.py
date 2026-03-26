import re

with open('static/js/main.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and show processContent
idx = content.find('processContent')
if idx != -1:
    print(f"Found at index: {idx}")
    print("Content around that area:")
    # Show the actual bytes
    segment = content[idx:idx+400]
    # Write to a debug file
    with open('debug_output.txt', 'w', encoding='utf-8') as out:
        out.write(segment)
    print("Written to debug_output.txt")
else:
    print("processContent not found")