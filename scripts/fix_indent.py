"""Fix indentation of the template block in dashboard.py"""
with open("/workspace/extreme-reversal-strategy/output/dashboard.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the html = f line and return html
html_start = None
html_end = None

for i, line in enumerate(lines):
    if "html = f" in line and "<!DOCTYPE" in line:
        html_start = i
    if html_start is not None and i > html_start:
        if line.strip() == "return html":
            html_end = i
            break

print(f"html = f at line {html_start+1}, return html at line {html_end+1}")

if html_start is not None and html_end is not None:
    current_indent = len(lines[html_start]) - len(lines[html_start].lstrip())
    print(f"Current indent: {current_indent}")
    
    if current_indent == 0:
        # Add 4 spaces to all non-empty lines in the range
        for i in range(html_start, html_end + 1):
            if lines[i].strip():
                lines[i] = "    " + lines[i]
        print("Added 4 spaces indent")
    
    with open("/workspace/extreme-reversal-strategy/output/dashboard.py", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Saved")

# Verify syntax
import py_compile
try:
    py_compile.compile("/workspace/extreme-reversal-strategy/output/dashboard.py", doraise=True)
    print("Syntax OK!")
except py_compile.PyCompileError as e:
    print(f"Syntax error: {e}")
