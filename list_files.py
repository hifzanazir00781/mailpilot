import os
from pathlib import Path

print("=" * 60)
print("PROJECT STRUCTURE")
print("=" * 60)

base = Path(".")
exclude_dirs = {'__pycache__', '.git', '.venv', 'venv', 'chroma_db', 'node_modules'}
exclude_files = {'.pyc', '.db', '.backup'}

for root, dirs, files in os.walk(base):
    # Skip excluded dirs
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    
    level = root.replace(str(base), '').count(os.sep)
    indent = '  ' * level
    
    # Print folder name
    if level > 0:
        print(f"{indent}📁 {os.path.basename(root)}/")
    
    # Print files
    sub_indent = '  ' * (level + 1)
    for file in sorted(files):
        if file.endswith(('.py', '.txt', '.md', '.env', '.gitignore')):
            ext = os.path.splitext(file)[1]
            icon = "🐍" if ext == '.py' else "📄" if ext == '.txt' else "📝" if ext == '.md' else "⚙️"
            print(f"{sub_indent}{icon} {file}")