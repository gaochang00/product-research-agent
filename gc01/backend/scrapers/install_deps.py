"""
安装爬虫依赖 — 以管理员身份运行
"""
import subprocess
import sys
import os

DEPS = [
    "playwright",
    "openpyxl",
]

print("=" * 50)
print("  安装亚马逊爬虫依赖")
print("=" * 50)

python = sys.executable

# 1. 安装pip包
for dep in DEPS:
    print(f"\n📦 正在安装 {dep}...")
    result = subprocess.run(
        [python, "-m", "pip", "install", dep],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"   ✅ {dep} 安装成功")
    else:
        print(f"   ❌ {dep} 安装失败: {result.stderr}")

# 2. 检查 Chrome 是否已安装
print("\n🔍 检查系统Chrome浏览器...")
chrome_paths = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]
chrome_found = any(os.path.exists(p) for p in chrome_paths)
if chrome_found:
    print("   ✅ 系统Chrome已安装，无需额外下载浏览器引擎")
else:
    print("   ⚠️ 未找到系统Chrome，请确保已安装Chrome浏览器")

print("\n" + "=" * 50)
print("✅ 安装完成！")
print("   现在可以运行: python amazon_scraper.py")
print("=" * 50)