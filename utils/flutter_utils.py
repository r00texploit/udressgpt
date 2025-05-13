from pathlib import Path
import subprocess

def validate_flutter_environment():
    try:
        result = subprocess.run(['flutter', '--version'], 
                               capture_output=True, 
                               text=True,
                               check=True)
        print("Flutter Environment Validated:")
        print(result.stdout)
        return True
    except Exception as e:
        print(f"Flutter Validation Error: {str(e)}")
        return False