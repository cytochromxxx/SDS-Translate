with open('static/js/main.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Try to find processContent and show the exact pattern
import re

# Use regex to find the processContent function
pattern = r'processContent\s*=\s*\(content\)\s*=>\s*\{[^}]+\}'
matches = re.findall(pattern, content)
if matches:
    print(f"Found {len(matches)} matches")
    for m in matches[:1]:
        print(repr(m[:200]))
else:
    print("No regex matches found")

# Try direct replacement
old = "processContent = (content) => {\n                    if (content && content.includes('</head>')) {\n                        return content.replace('</head>', editingCSS + '</head>');\n                    } else if (content && content.includes('<html>')) {\n                        return '<html><head>' + editingCSS + '</head><body>' + content.replace(/<html>|</html>|<body>|</body>/g, '') + '</body></html>';\n                    }\n                    return content;\n                };"
                    
new = "processContent = (content) => {\n                    if (!content) return '';\n                    if (content.includes('</head>')) {\n                        return content.replace('</head>', editingCSS + '</head>');\n                    } else if (content.includes('<html>')) {\n                        return '<html><head>' + editingCSS + '</head><body>' + content.replace(/<html>|</html>|<body>|</body>/g, '') + '</body></html>';\n                    } else {\n                        return '<html><head>' + editingCSS + '</head><body>' + content + '</body></html>';\n                    }\n                };"

with open('fix_result.txt', 'w', encoding='utf-8') as f:
    if old in content:
        content = content.replace(old, new)
        with open('static/js/main.js', 'w', encoding='utf-8') as ff:
            ff.write(content)
        f.write("SUCCESS - Replacement made")
    else:
        f.write("Old pattern not found")