import re

sample = """*   **Intellectually Curious:** Driven by knowledge.
*   **Methodical:** Careful and planned."""

# Test different regex patterns
print("Original:")
print(sample)
print("\n" + "="*50)

# Try pattern 1
result1 = re.sub(r'\*\s+\*\*(.+?)\*\*:\s*', r'• \1:\n', sample)
print("Pattern 1:")
print(result1)
print("\n" + "="*50)

# Try pattern 2 - match the actual structure
result2 = re.sub(r'\*\s+\*\*([^*]+)\*\*:\s*([^\n]+)', r'• \1:\n  \2', sample)
print("Pattern 2:")
print(result2)
print("\n" + "="*50)

# Try pattern 3 - simpler
result3 = re.sub(r'\*\s+\*\*', '• ', sample)
result3 = result3.replace('**', '')
print("Pattern 3:")
print(result3)
