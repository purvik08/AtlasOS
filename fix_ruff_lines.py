with open(r'D:\AtlasOS\src\atlas\ui\desktop\cli\desktop.py', 'r') as f:
    lines = f.readlines()

# Fix line 51 (index 50): System status f-string (116 chars -> break into 2 lines)
old51 = 'console.print(f"[bold]System:[/] {system.status if not system.error else \\'Error: \\' + system.error}")\\n'
new51 = 'msg = system.status if not system.error else "Error: " + system.error\\n                console.print(f"[bold]System:[/] {msg}")\\n'
lines[50] = new51

# Fix line 60 (index 59): Models f-string (109 chars -> break into 2 lines)
old60 = 'console.print(f"\\n[bold]Models:[/] {models.total_count} total, {models.loaded_count} loaded")\\n'
new60 = 'console.print(f"\\n[bold]Models:[/] {models.total_count} total")\\n                console.print(f"  Loaded: {models.loaded_count}")\\n'
lines[59] = new60

# Fix line 72 (index 71): Provider status f-string (111 chars -> break into 2 lines)
old72 = 'console.print(f"  [{status_color}]{p.name}: {p.status.value}[/] ({p.models_count} models)")\\n'
new72 = 'status_str = f"[{status_color}]{p.name}: {p.status.value}"\\n                console.print(f"  {status_str} ({p.models_count} models)")\\n'
lines[71] = new72

# Fix line 136 (index 135): Backend status f-string (112 chars -> break into 2 lines)
old136 = 'console.print(f"[bold]Backend Status:[/] {url}")\\n'
new136 = 'backend_str = "[bold]Backend Status:[/] " + url\\n                console.print(backend_str)\\n'
lines[135] = new136

# Fix line 145 (index 144): Models f-string (105 chars -> break into 2 lines)
old145 = 'console.print(f"\\n[bold]Models:[/] {models.total_count} total, {models.loaded_count} loaded")\\n'
new145 = 'console.print(f"\\n[bold]Models:[/] {models.total_count} total")\\n                console.print(f"  Loaded: {models.loaded_count}")\\n'
lines[143] = new145

# Fix line 157 (index 156): Provider status f-string (107 chars -> break into 2 lines)
old157 = 'console.print(f"  [{status_color}]{p.name}: {p.status.value}[/] ({p.models_count} models)")\\n'
new157 = 'status_str = f"[{status_color}]{p.name}: {p.status.value}"\\n                console.print(f"  {status_str} ({p.models_count} models)")\\n'
lines[155] = new157

with open(r'D:\AtlasOS\src\atlas\ui\desktop\cli\desktop.py', 'w') as f:
    f.writelines(lines)
print("Fixed desktop.py long lines")