"""Fix nested f-string in dashboard.py"""
import re

with open("/workspace/extreme-reversal-strategy/output/dashboard.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Find and replace the nested f-string block
idx1 = content.find("{f'''")
if idx1 >= 0:
    # Find the matching end by counting quotes
    end_str = "''' if inflow_html else ''}"
    idx2 = content.find(end_str, idx1)
    if idx2 >= 0:
        idx2 += len(end_str)
        # Replace the whole block
        block = content[idx1:idx2]
        print(f"Found nested f-string block ({len(block)} chars)")
        print(f"Starts with: {block[:60]!r}")
        print(f"Ends with: {block[-60:]!r}")
        content = content[:idx1] + "{sector_fund_card}" + content[idx2:]
        print("Replaced!")

# 2. Add sector_fund_card variable before the template
var_code = """
    # 板块资金流向卡片HTML
    sector_fund_card = ""
    if inflow_html:
        sector_fund_card = '''                <div class="market-card" style="grid-column: span 2;">
                    <div class="label" style="font-size:13px">\U0001f4c8 板块主力资金流向 TOP5</div>
                    <div class="label" style="margin-top:4px;font-size:12px;line-height:1.8">''' + \"{inflow_html}\" + '''</div>
                    <div class="label" style="margin-top:2px;font-size:12px;line-height:1.8">''' + \"{outflow_html}\" + '''</div>
                </div>
'''
"""

template_start = content.find("html = f'''<!DOCTYPE")
if template_start >= 0:
    content = content[:template_start] + "    " + var_code.strip() + "\n    " + content[template_start:]
    print(f"Added sector_fund_card before template")

# 3. Count remaining issues
remaining = content.count("{f'''")
print(f"Remaining nested f-strings: {remaining}")

with open("/workspace/extreme-reversal-strategy/output/dashboard.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
