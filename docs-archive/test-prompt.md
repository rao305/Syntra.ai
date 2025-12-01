# Test Prompt for IDE Configuration

Use this test prompt with your AI assistant to verify the system prompt is working correctly.

## Test Request

Copy and paste this request to your AI assistant:

```
Explain the time complexity of binary search and show a TypeScript implementation. Use proper mathematical notation and code formatting.
```

## Expected Response Format

Your AI assistant should respond with:

### ✅ Mathematical Notation
- Time complexity as LaTeX: `$O(\log n)$`
- Space complexity as LaTeX: `$O(1)$`
- Mathematical formulas properly formatted

### ✅ Code Block
```typescript
function binarySearch<T>(arr: T[], target: T): number {
  let left = 0;
  let right = arr.length - 1;
  
  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    
    if (arr[mid] === target) {
      return mid;
    } else if (arr[mid] < target) {
      left = mid + 1;
    } else {
      right = mid - 1;
    }
  }
  
  return -1;
}
```

### ✅ Markdown Structure
- Proper headings (`#`, `##`, `###`)
- Clear explanations
- No HTML tags unless specifically requested

## Verification Checklist

- [ ] Math appears as rendered LaTeX (not raw `$` symbols)
- [ ] Code block has dark background with syntax highlighting
- [ ] Code block specifies language (`typescript`)
- [ ] Response is well-structured with headings
- [ ] No explanatory text inside the code fence
- [ ] Complete, runnable code example

## Common Issues

### ❌ Raw LaTeX symbols
If you see `$O(\log n)$` as plain text instead of formatted math, the system prompt may not be loaded correctly.

### ❌ No code highlighting
If the code appears as plain text, check that fenced code blocks have language tags.

### ❌ Inconsistent formatting
If responses vary in format, the system prompt configuration may need adjustment.

## Success Indicators

When working correctly, your AI assistant will:
1. **Always** use LaTeX for mathematical expressions
2. **Always** use fenced code blocks with language tags
3. **Always** structure responses with Markdown
4. Provide complete, copy-pastable code examples
5. Follow the project's TypeScript/React patterns