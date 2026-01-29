import subprocess
import os
import sys
import json
import plistlib

def get_version_from_config():
    """从配置文件获取版本号"""
    try:
        with open('version.json', 'r') as f:
            config = json.load(f)
            return config.get('version', '1.0.0')
    except FileNotFoundError:
        print("⚠️  未找到 version.json 文件，使用默认版本号 1.0.0")
        return '1.0.0'

def modify_info_plist(app_path, version):
    """修改已生成的应用程序的 Info.plist 文件"""
    info_plist_path = os.path.join(app_path, 'Contents', 'Info.plist')
    
    if not os.path.exists(info_plist_path):
        print(f"⚠️  Info.plist 文件不存在: {info_plist_path}")
        return False
    
    try:
        # 读取现有的 Info.plist
        with open(info_plist_path, 'rb') as f:
            plist_data = plistlib.load(f)
        
        # 更新版本信息
        plist_data['CFBundleShortVersionString'] = version
        plist_data['CFBundleVersion'] = version
        plist_data['CFBundleGetInfoString'] = version
        plist_data['CFBundleName'] = f'Macked v{version}'
        
        # 写回 Info.plist
        with open(info_plist_path, 'wb') as f:
            plistlib.dump(plist_data, f)
        
        print(f"✅ Info.plist 已更新版本号为: {version}")
        return True
    except Exception as e:
        print(f"❌ 修改 Info.plist 失败: {e}")
        return False

def build_mac_app():
    """构建macOS应用程序包"""
    print("开始构建macOS应用程序...")
    
    version = get_version_from_config()
    print(f"使用版本号: {version}")
    
    main_script = "macked.py"
    icon_file = "macked.icns"
    
    # 检查主脚本是否存在
    if not os.path.exists(main_script):
        print(f"❌ 错误: 未找到主脚本 {main_script}")
        return False
    
    # 检查图标文件
    if os.path.exists(icon_file):
        print(f"✅ 找到图标文件: {icon_file}")
    else:
        print(f"⚠️  未找到图标文件: {icon_file}")
    
    cmd = [
        "pyinstaller",
        "--windowed",
        "--onedir",
        f"--name=Macked",
        f"--osx-bundle-identifier=com.yourcompany.macked.v{version.replace('.', '_')}",
        "--add-data=macked.icns:.",
        "--add-data=version.json:.",
        "--hidden-import=PIL",
        "--hidden-import=requests",
        "--hidden-import=bs4",
        "--hidden-import=lxml",
    ]
    
    if os.path.exists(icon_file):
        cmd.append(f"--icon={icon_file}")
    
    cmd.append(main_script)
    
    print("执行命令:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 编译成功！")
        
        # 应用程序路径
        app_path = 'dist/Macked.app'
        
        # 修改 Info.plist 文件以设置版本号
        if modify_info_plist(app_path, version):
            print(f"✅ 应用程序版本号已成功设置为: {version}")
        else:
            print(f"⚠️  未能设置版本号")
            return False
        
        print(f"✅ 应用程序已生成: {app_path}")
        return True
    except subprocess.CalledProcessError as e:
        print("❌ 编译失败:")
        print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print("❌ 错误: 未找到 pyinstaller，请先安装它: pip install pyinstaller")
        return False

if __name__ == "__main__":
    print("Macked - macOS 应用构建工具")
    print("="*40)
    
    success = build_mac_app()
    
    if success:
        print("\n🎉 构建完成！")
        version = get_version_from_config()
        print(f"版本号: {version}")
        print("应用程序位置: dist/Macked.app/")
    else:
        print("\n💥 构建失败")
        sys.exit(1)