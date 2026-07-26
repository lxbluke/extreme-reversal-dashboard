"""Fix: replace nested f-string bar chart code with pre-computed HTML"""
import re

with open("/workspace/extreme-reversal-strategy/output/dashboard.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find and remove the broken _make_bar_row function
# It starts with "def _make_bar_row" and ends just before "html = f'''"
start = content.find("def _make_bar_row")
end = content.find("html = f'''<!DOCTYPE", start)

if start > 0 and end > start:
    print(f"Found broken function at {start}-{end}")
    # Remove everything from start to end
    content = content[:start] + content[end:]
    print("Removed broken function")
else:
    print(f"Function not found: start={start}, end={end}")

# Also remove the bar chart related template variable references that are now orphaned
content = content.replace("{extreme_bars_html}", "<!-- bars -->")
content = content.replace("{all_bars_html}", "<!-- bars -->")

# Now insert simple pre-computed bar chart code before the template
insert_point = content.find("html = f'''<!DOCTYPE")
if insert_point > 0:
    bar_code = '''
    # 预计算条形图HTML（避免f-string嵌套问题）
    bar_chart_extreme = ""
    bar_chart_all = ""
    try:
        ext_bars = []
        for s in extreme_signals[:10]:
            nm = s.get("asset_name", "")
            sc = s.get("composite_score", 0)
            wdt = min(abs(sc) * 100, 100)
            clr = "#4CAF50" if sc < 0 else "#DC3545"
            ext_bars.append(\'<div class="bar-row"><span class="bar-label">\' + nm + \'</span><div class="bar-track"><div class="bar-fill" style="width:\' + str(round(wdt)) + \'%;background:\' + clr + \'"></div></div><span class="bar-score" style="color:\' + clr + \'">\' + "{:+.2f}".format(sc) + \'</span></div>\')
        bar_chart_extreme = "\\n".join(ext_bars)
        
        all_bars = []
        for s in signals[:12]:
            nm = s.get("asset_name", "")
            sc = s.get("composite_score", 0)
            wdt = min(abs(sc) * 100, 100)
            clr = "#4CAF50" if sc < 0 else "#DC3545"
            all_bars.append(\'<div class="bar-row"><span class="bar-label">\' + nm + \'</span><div class="bar-track"><div class="bar-fill" style="width:\' + str(round(wdt)) + \'%;background:\' + clr + \'"></div></div><span class="bar-score" style="color:\' + clr + \'">\' + "{:+.2f}".format(sc) + \'</span></div>\')
        bar_chart_all = "\\n".join(all_bars)
    except Exception:
        bar_chart_extreme = "<!-- 图表渲染异常 -->"
        bar_chart_all = "<!-- 图表渲染异常 -->"
'''
    content = content[:insert_point] + bar_code + content[insert_point:]
    print("Inserted bar chart pre-computation code")

# Replace the <!-- bars --> placeholders with actual variables
content = content.replace("<!-- bars -->", "{bar_chart_extreme}", 1)
content = content.replace("<!-- bars -->", "{bar_chart_all}", 1)

with open("/workspace/extreme-reversal-strategy/output/dashboard.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
