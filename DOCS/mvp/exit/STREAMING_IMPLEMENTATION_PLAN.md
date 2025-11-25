# Streaming Implementation Plan

## Problem
- Non-streaming LLM calls timeout after 10 minutes
- Large specs generate massive JSON responses (>50K tokens)
- Current implementation blocks on response collection

## Solution: Streaming Mode

### 1. Trigger Condition
```python
# In _generate_with_llm()
# Spec > 20KB → Use streaming
if len(spec_markdown) > 20000:
    return await self._generate_with_streaming(prompt, spec_markdown)
```

### 2. Implementation Changes

#### File: `src/specs/spec_to_application_ir.py`

**New Method: `_generate_with_streaming()`**
```python
async def _generate_with_streaming(self, prompt: str, spec: str) -> str:
    """Stream response from LLM for large specs."""
    response_text = ""

    with self.client.messages.stream(
        model=self.LLM_MODEL,
        max_tokens=32000,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    ) as stream:
        for text in stream.text_stream:
            response_text += text
            # Optional: log progress every 5KB
            if len(response_text) % 5000 == 0:
                logger.debug(f"Streamed {len(response_text)} chars...")

    return response_text
```

**Modify: `_generate_with_llm()`**
```python
async def _generate_with_llm(self, prompt: str, spec_markdown: str) -> str:
    """Generate IR data from spec using LLM."""
    try:
        if len(spec_markdown) > 20000:
            logger.info("Spec > 20KB → using streaming mode")
            return await self._generate_with_streaming(prompt, spec_markdown)

        # Original non-streaming path for small specs
        response = await self.client.messages.create(
            model=self.LLM_MODEL,
            max_tokens=32000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise
```

### 3. Benefits
- ✅ Unblocks processing of large specs (>20KB)
- ✅ No timeout errors on complex domains
- ✅ Keeps small specs fast (non-streaming)
- ✅ Progressive response collection (memory efficient)

### 4. Testing Strategy
```bash
# Test 1: Small spec (non-streaming)
python /tmp/test_flow_simple.py  # Task API spec (~2KB)

# Test 2: Large spec (streaming)
python /tmp/test_flow_large.py   # E-commerce spec (~50KB)
```

### 5. Validation Checklist
- [ ] Small specs still work (no streaming)
- [ ] Large specs complete without timeout
- [ ] JSON extraction handles streamed responses
- [ ] BehaviorModelIR.flows populated correctly
- [ ] No hardcoding in extracted flows

### 6. Risk Mitigation
- Streaming preserves response order (no issues)
- JSON extraction already handles partial/malformed JSON
- No additional error handling needed (stream errors bubble up)
- Backward compatible (fallback to non-streaming for small specs)

## Timeline
- Phase 1: Implement `_generate_with_streaming()` (30 min)
- Phase 2: Modify `_generate_with_llm()` trigger logic (10 min)
- Phase 3: Test both paths (30 min)
- Phase 4: Validate BehaviorModelIR extraction (20 min)
