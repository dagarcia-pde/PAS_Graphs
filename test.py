import sys

code_path = r'\\azshfs.intel.com\AZAnalysis$\1272_MAODATA\Config\PDE\dagarcia\PAS_CODE'

print(f"Adding code path: {code_path}")

sys.path.append(code_path)

try:
    import Class_PAS_Data_Extract
    import Class_PAS_Product
    import Class_PAS_Email
    import Class_PAS_Graph
    print("Package imported successfully!")
except ImportError as e:
    print(f"Failed to import package. Error: {e}")