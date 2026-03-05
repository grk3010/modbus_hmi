import sys
import pkg_resources

libs = ["pymodbus", "nicegui", "lxml", "pandas"]
print(f"Python Path: {sys.executable}")

for lib in libs:
    try:
        version = pkg_resources.get_distribution(lib).version
        print(f"✅ {lib} version {version} is ready.")
    except pkg_resources.DistributionNotFound:
        print(f"❌ {lib} is NOT installed.")
