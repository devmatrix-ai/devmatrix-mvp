"""
Script to fix async/await issues in test_acceptance_test_generator.py

Fixes:
1. Make scalar_one_or_none() synchronous (MagicMock instead of AsyncMock)
2. Make scalars().all() synchronous
3. Ensure execute returns proper mock structure
"""
import re

# Read the test file
with open('/home/kwar/code/agentic-ai/tests/unit/testing/test_acceptance_test_generator.py', 'r') as f:
    content = f.read()

# Pattern 1: Fix scalar_one_or_none pattern
# FROM:
#   mock_result = AsyncMock()
#   mock_result.scalar_one_or_none.return_value = masterplan
# TO:
#   mock_result = Mock()
#   mock_result.scalar_one_or_none.return_value = masterplan

# Replace AsyncMock() with Mock() for result objects
# This is safe because the result object itself is not async, only execute() is async
content = re.sub(
    r'(\s+)mock_result = AsyncMock\(\)\n(\s+)mock_result\.scalar_one_or_none',
    r'\1mock_result = Mock()\n\2mock_result.scalar_one_or_none',
    content
)

# Pattern 2: Fix scalars().all() pattern
# FROM:
#   mock_result = AsyncMock()
#   mock_result.scalars.return_value.all.return_value = tests
# TO:
#   mock_result = Mock()
#   mock_scalars = Mock()
#   mock_scalars.all.return_value = tests
#   mock_result.scalars.return_value = mock_scalars

# Find all scalars().all() patterns and rewrite them
def fix_scalars_all(match):
    indent = match.group(1)
    var_name = match.group(2)
    return_value = match.group(3)

    return f'''{indent}mock_result = Mock()
{indent}mock_scalars = Mock()
{indent}mock_scalars.all.return_value = {return_value}
{indent}mock_result.scalars.return_value = mock_scalars'''

content = re.sub(
    r'(\s+)mock_result = (?:Async)?Mock\(\)\n\s+mock_result\.scalars\.return_value\.all\.return_value = ([^\n]+)',
    fix_scalars_all,
    content
)

# Add Mock import if not present
if 'from unittest.mock import AsyncMock, MagicMock, patch' in content:
    content = content.replace(
        'from unittest.mock import AsyncMock, MagicMock, patch',
        'from unittest.mock import AsyncMock, MagicMock, Mock, patch'
    )

# Write the updated file
with open('/home/kwar/code/agentic-ai/tests/unit/testing/test_acceptance_test_generator.py', 'w') as f:
    f.write(content)

print("✅ Fixed async/await issues in test_acceptance_test_generator.py")
print("Changes:")
print("  - Changed AsyncMock() to Mock() for result objects (scalar_one_or_none is synchronous)")
print("  - Fixed scalars().all() pattern to use Mock instead of AsyncMock")
print("  - Added Mock to imports")
