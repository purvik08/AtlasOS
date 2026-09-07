import sys
sys.path.insert(0, r'D:\AtlasOS\src')
from atlas.cli.main import cli
from click.testing import CliRunner

runner = CliRunner()

# Test desktop start --no-gui
result = runner.invoke(cli, ['desktop', 'start', '--no-gui'])
print('=== desktop start --no-gui ===')
print('Exit code:', result.exit_code)
print('Output:', result.output)
if result.exception:
    import traceback
    traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
print()

# Test desktop status
result2 = runner.invoke(cli, ['desktop', 'status', '--url', 'http://localhost:8000'])
print('=== desktop status ===')
print('Exit code:', result2.exit_code)
print('Output:', result2.output)
if result2.exception:
    import traceback
    traceback.print_exception(type(result2.exception), result2.exception, result2.exception.__traceback__)
print()

# Test desktop --help
result3 = runner.invoke(cli, ['desktop', '--help'])
print('=== desktop --help ===')
print('Exit code:', result3.exit_code)
print('Output:', result3.output)