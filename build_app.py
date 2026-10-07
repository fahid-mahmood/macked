import subprocess
import os
import sys
import json
import plistlib

def get_version_from_config():
    """Read the version number from the config file"""
    try:
        with open('version.json', 'r') as f:
            config = json.load(f)
            return config.get('version', '1.0.0')
    except FileNotFoundError:
        print("⚠️  version.json not found, using default version 1.0.0")
        return '1.0.0'

def modify_info_plist(app_path, version):
    """Modify the generated app bundle's Info.plist"""
    info_plist_path = os.path.join(app_path, 'Contents', 'Info.plist')

    if not os.path.exists(info_plist_path):
        print(f"⚠️  Info.plist does not exist: {info_plist_path}")
        return False

    try:
        # Read the existing Info.plist
        with open(info_plist_path, 'rb') as f:
            plist_data = plistlib.load(f)

        # Update version information
        plist_data['CFBundleShortVersionString'] = version
        plist_data['CFBundleVersion'] = version
        plist_data['CFBundleGetInfoString'] = version
        plist_data['CFBundleName'] = f'Macked v{version}'

        # Write Info.plist back
        with open(info_plist_path, 'wb') as f:
            plistlib.dump(plist_data, f)

        print(f"✅ Info.plist updated with version: {version}")
        return True
    except Exception as e:
        print(f"❌ Failed to modify Info.plist: {e}")
        return False

def build_mac_app():
    """Build the macOS app bundle"""
    print("Building macOS app...")

    version = get_version_from_config()
    print(f"Using version: {version}")

    main_script = "macked.py"
    icon_file = "macked.icns"

    # Check that the main script exists
    if not os.path.exists(main_script):
        print(f"❌ Error: main script not found: {main_script}")
        return False

    # Check the icon file
    if os.path.exists(icon_file):
        print(f"✅ Icon file found: {icon_file}")
    else:
        print(f"⚠️  Icon file not found: {icon_file}")

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

    print("Running:", " ".join(cmd))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Build succeeded!")

        # App bundle path
        app_path = 'dist/Macked.app'

        # Modify Info.plist to set the version number
        if modify_info_plist(app_path, version):
            print(f"✅ App version set to: {version}")
        else:
            print(f"⚠️  Could not set the version number")
            return False

        print(f"✅ App generated: {app_path}")
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Build failed:")
        print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print("❌ Error: pyinstaller not found. Install it first: pip install pyinstaller")
        return False

if __name__ == "__main__":
    print("Macked - macOS app build tool")
    print("="*40)

    success = build_mac_app()

    if success:
        print("\n🎉 Build complete!")
        version = get_version_from_config()
        print(f"Version: {version}")
        print("App location: dist/Macked.app/")
    else:
        print("\n💥 Build failed")
        sys.exit(1)
