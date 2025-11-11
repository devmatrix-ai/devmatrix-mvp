# 🔴 P0 Critical Fixes - Implementation Guide

## Summary
Three CRITICAL issues identified in RAG system require fixes this week. These are production-breaking bugs with high-impact remediation.

---

## Fix #1: FastAPI Background Task - File I/O Race Condition

**Severity:** 🔴 CRITICAL
**Code ID:** `47a04ff3-af4b-4388-97ef-4b6779c36b19`
**Affected:** 28 examples (18.7%)
**Timeline:** 2 hours
**Impact:** Race conditions, data loss, crash on shutdown

### Current Buggy Code
```python
# ❌ BUGGY - Found in verification.json
from fastapi import FastAPI, BackgroundTasks

def write_log(message: str):
    with open("log.txt", "a") as f:  # Race condition!
        f.write(message + "\n")

app = FastAPI()

@app.post("/notify/")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(write_log, f"Email sent to {email}")
    return {"message": "Notification will be sent in the background"}
```

### Problems Identified
1. **Race Condition:** Multiple concurrent requests write to same file without locking
2. **String Injection:** Unsanitized email input in log message
3. **No Error Handling:** File write failures crash silently
4. **Hard-coded Path:** Not portable across environments
5. **No Resource Cleanup:** File handle leaks possible

### Fixed Code
```python
# ✅ FIXED
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
import os

# Configure structured logging with rotation
def setup_logger(log_file: Optional[str] = None) -> logging.Logger:
    """Setup application logger with rotating file handler."""
    if log_file is None:
        log_file = os.getenv("APP_LOG_FILE", "app.log")

    logger = logging.getLogger("app_notifications")
    if logger.handlers:  # Avoid duplicate handlers
        return logger

    # Create logs directory if needed
    log_path = Path(log_file).parent
    log_path.mkdir(parents=True, exist_ok=True)

    # Rotating file handler: 10MB max, keep 5 backups
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10_000_000,
        backupCount=5
    )

    # Structured format with timestamp
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger

logger = setup_logger()

from fastapi import FastAPI, BackgroundTasks
from pydantic import EmailStr, BaseModel

class NotificationRequest(BaseModel):
    email: EmailStr  # Validated email
    message: str

app = FastAPI()

async def log_notification_safe(email: str, message: str):
    """Safely log notification with error handling."""
    try:
        # Sanitize email: remove newlines and special chars
        sanitized_email = email.replace("\n", "").replace("\r", "")
        sanitized_msg = message.replace("\n", " ")[:200]  # Max 200 chars

        logger.info(
            f"Notification sent | email={sanitized_email} | message={sanitized_msg}"
        )
    except Exception as e:
        logger.error(
            f"Failed to log notification for {email}",
            exc_info=True,
            extra={"error": str(e)}
        )
        # Don't raise - background task failure shouldn't crash app

@app.post("/notify/")
async def send_notification(
    request: NotificationRequest,
    background_tasks: BackgroundTasks
):
    """Send notification with safe background logging."""
    # Add to background tasks
    background_tasks.add_task(
        log_notification_safe,
        request.email,
        request.message
    )

    return {
        "status": "pending",
        "message": "Notification will be sent in background"
    }
```

### Key Improvements
✅ Uses Python's `logging` module (thread-safe)
✅ RotatingFileHandler prevents file growth
✅ Input validation with Pydantic EmailStr
✅ Sanitization of email/message data
✅ Proper error handling with logging
✅ Environment-aware file paths
✅ No race conditions

### Testing
```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_notification_logging(tmp_path):
    """Test notification logging works safely."""
    import os
    os.environ["APP_LOG_FILE"] = str(tmp_path / "test.log")

    client = TestClient(app)

    # Send concurrent notifications
    for i in range(10):
        response = client.post(
            "/notify/",
            json={"email": f"user{i}@example.com", "message": f"Test {i}"}
        )
        assert response.status_code == 202

    # Verify log file exists and has content
    log_file = tmp_path / "test.log"
    assert log_file.exists()
    content = log_file.read_text()
    assert "user0@example.com" in content

@pytest.mark.asyncio
async def test_notification_with_invalid_email():
    """Test that invalid email is rejected."""
    client = TestClient(app)

    response = client.post(
        "/notify/",
        json={"email": "not-an-email", "message": "Test"}
    )
    # Should fail validation before background task
    assert response.status_code == 422
```

---

## Fix #2: FastAPI Response Model - Truthiness Bug

**Severity:** 🔴 CRITICAL
**Code ID:** `f7cd7a35-a101-4562-abc7-d2ede1adad3a`
**Affected:** 30 examples (20.0%)
**Timeline:** 1 hour
**Impact:** Incorrect price calculations when tax=0

### Current Buggy Code
```python
# ❌ BUGGY - Found in verification.json
from fastapi import FastAPI, status
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    tax: float = 10.5

app = FastAPI()

@app.post("/items/", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(item: Item):
    item_dict = item.dict()
    if item.tax:  # ❌ BUG: Fails when tax=0.0!
        price_with_tax = item.price + item.tax
        item_dict.update({"price_with_tax": price_with_tax})
    return item_dict
```

### Problem
The condition `if item.tax:` treats 0 as False (Python truthiness), so:
- tax=10.5 → calculates price_with_tax ✅
- tax=0.0  → skips calculation ❌
- tax=None → skips calculation ✓ (but would be good to handle)

### Fixed Code - Option A (Simple Fix)
```python
# ✅ FIXED - Option A: Explicit None check
from fastapi import FastAPI, status
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str
    description: str = None
    price: float = Field(..., gt=0, description="Price must be positive")
    tax: float = Field(default=0.0, ge=0, description="Tax percentage")
    tags: list[str] = []

app = FastAPI()

@app.post("/items/", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(item: Item):
    item_dict = item.dict()

    # ✅ Fixed: Check if tax is not None, not if it's truthy
    if item.tax is not None and item.tax > 0:
        price_with_tax = item.price * (1 + item.tax / 100)
        item_dict.update({"price_with_tax": price_with_tax})

    return item_dict
```

### Fixed Code - Option B (Best Practice)
```python
# ✅ FIXED - Option B: Always calculate with validators
from fastapi import FastAPI, status
from pydantic import BaseModel, Field, validator
from typing import Optional

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    tax: float = Field(default=0.0, ge=0, le=100)
    tags: list[str] = []

    @validator('price', 'tax', pre=True)
    def ensure_float(cls, v):
        """Ensure numeric fields are proper floats."""
        if v is None:
            return 0.0
        return float(v)

class ItemWithTax(Item):
    """Response model including calculated tax."""
    price_with_tax: float
    tax_amount: float

app = FastAPI()

@app.post("/items/", response_model=ItemWithTax, status_code=status.HTTP_201_CREATED)
async def create_item(item: Item):
    """Create item with tax calculation."""
    # Always calculate, even when tax=0
    tax_amount = item.price * (item.tax / 100) if item.tax > 0 else 0.0
    price_with_tax = item.price + tax_amount

    item_dict = item.dict()
    item_dict.update({
        "tax_amount": tax_amount,
        "price_with_tax": price_with_tax
    })

    return ItemWithTax(**item_dict)

@app.get("/items/", response_model=list[ItemWithTax])
async def read_items():
    """Retrieve all items with tax calculations."""
    items = [
        Item(name="Foo", price=50),
        Item(name="Bar", description="Bartenders", price=62, tax=20),
        Item(name="Baz", price=50.2, tax=10, tags=["tag1"]),
    ]

    return [
        ItemWithTax(
            **item.dict(),
            tax_amount=item.price * (item.tax / 100),
            price_with_tax=item.price * (1 + item.tax / 100)
        )
        for item in items
    ]
```

### Key Improvements
✅ Explicit None check (not truthiness)
✅ Input validation with Field constraints
✅ Separate response model for calculated fields
✅ Always calculates correctly (even tax=0)
✅ Type hints for all fields
✅ Docstrings for clarity

### Testing
```python
import pytest
from fastapi.testclient import TestClient

def test_item_with_zero_tax():
    """Test that tax=0 is handled correctly."""
    client = TestClient(app)

    response = client.post(
        "/items/",
        json={
            "name": "FreeItem",
            "price": 100.0,
            "tax": 0.0
        }
    )

    assert response.status_code == 201
    data = response.json()

    # Key assertion: tax_amount and price_with_tax should be calculated
    assert data["price"] == 100.0
    assert data["tax"] == 0.0
    assert data["tax_amount"] == 0.0  # ✅ Correctly 0, not missing
    assert data["price_with_tax"] == 100.0  # ✅ Correctly matches price

def test_item_with_nonzero_tax():
    """Test normal tax calculation."""
    client = TestClient(app)

    response = client.post(
        "/items/",
        json={
            "name": "TaxedItem",
            "price": 100.0,
            "tax": 10.0  # 10%
        }
    )

    assert response.status_code == 201
    data = response.json()

    assert data["price"] == 100.0
    assert data["tax"] == 10.0
    assert data["tax_amount"] == 10.0  # 100 * 10%
    assert data["price_with_tax"] == 110.0  # 100 + 10

def test_invalid_negative_price():
    """Test validation rejects negative prices."""
    client = TestClient(app)

    response = client.post(
        "/items/",
        json={
            "name": "InvalidItem",
            "price": -50.0,  # Invalid
            "tax": 0.0
        }
    )

    assert response.status_code == 422  # Validation error
```

---

## Fix #3: Reduce Code Duplication

**Severity:** 🔴 CRITICAL
**Current State:** 96% duplication ratio (150 examples = 6 unique)
**Timeline:** 1-2 hours
**Impact:** Severely limited retrieval diversity

### Root Cause
The MMR (Maximal Marginal Relevance) retrieval strategy is selecting the same 5-6 examples repeatedly because:
1. They have high relevance scores (0.81+ similarity)
2. MMR diversity penalty is too weak
3. No diversity enforcement across different queries

### Solution: Adjust MMR Penalty in Retriever

**File to modify:** `src/rag/retriever.py`

**Current code (line ~280):**
```python
# Current: weak diversity penalty
mmr_score = (1 - lambda_param) * similarity_score - lambda_param * max_diversity
# With lambda=0.6: mostly relevance-focused, weak diversity
```

**Fixed code:**
```python
# Enhanced diversity enforcement
def _retrieve_mmr(self, context, top_k, min_similarity, filters=None):
    """
    Retrieve with Maximal Marginal Relevance.

    Enhanced version with stronger diversity penalty to prevent
    the same examples being returned for all queries.
    """

    # Step 1: Get candidate results (top 20 to choose from)
    candidates = self.vector_store.search_with_metadata(
        query_embedding=context.query_embedding,
        top_k=top_k * 4,  # Get 4x candidates to select diverse subset
        min_similarity=min_similarity,
        filters=filters
    )

    if not candidates:
        return []

    selected = []
    candidate_ids = {doc.id for doc in candidates}

    # Lambda balances relevance vs diversity
    # Higher lambda = more diversity penalty
    lambda_param = 0.5  # Default: 50% relevance, 50% diversity

    while selected and len(selected) < top_k and candidate_ids:
        best_score = -float('inf')
        best_candidate = None

        for candidate in candidates:
            if candidate.id in candidate_ids:
                # Relevance component
                relevance = candidate.similarity

                # Diversity component: penalize similarity to already selected
                diversity = 0
                for selected_doc in selected:
                    # Penalize if similar to any selected document
                    diversity += self._compute_similarity(
                        candidate.embedding,
                        selected_doc.embedding
                    )

                # Normalize diversity to [0, 1]
                if selected:
                    diversity = diversity / len(selected)

                # Compute MMR score with STRONGER diversity penalty
                mmr_score = (1 - lambda_param) * relevance - lambda_param * diversity

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_candidate = candidate

        if best_candidate:
            selected.append(best_candidate)
            candidate_ids.remove(best_candidate.id)
        else:
            break

    # Convert to RetrievalResult format
    results = [
        RetrievalResult(
            id=doc.id,
            code=doc.metadata.get("code", ""),
            metadata=doc.metadata,
            similarity=doc.similarity,
        )
        for doc in selected
    ]

    return results
```

### Alternative Quick Fix (If full rewrite not feasible)

Modify just the lambda parameter in existing code:

```python
# In _retrieve_mmr method, find this line:
lambda_param = 0.6  # ← CHANGE THIS

# To:
lambda_param = 0.3  # More aggressive diversity (70% diversity, 30% relevance)

# Or even stronger:
lambda_param = 0.2  # Maximum diversity (80% diversity, 20% relevance)
```

### Testing Diversity Improvement

```python
import pytest
from src.rag.retriever import Retriever, RetrievalStrategy

@pytest.mark.asyncio
async def test_mmr_diversity():
    """Test that MMR returns diverse examples."""
    retriever = Retriever(enable_v2_caching=False)

    # Make multiple different queries
    queries = [
        "repository pattern with SQLAlchemy",
        "async database queries",
        "ORM best practices",
        "API endpoint design",
        "error handling patterns"
    ]

    all_retrieved_ids = []

    for query in queries:
        results = retriever.retrieve(
            query,
            strategy=RetrievalStrategy.MMR,
            top_k=3
        )

        retrieved_ids = [r.id for r in results]
        all_retrieved_ids.extend(retrieved_ids)

        print(f"Query: {query}")
        print(f"  Results: {retrieved_ids}")

    # Check diversity: should see many different IDs, not same 5-6
    unique_ids = set(all_retrieved_ids)
    total_results = len(all_retrieved_ids)

    diversity_ratio = len(unique_ids) / total_results

    print(f"\nDiversity Statistics:")
    print(f"  Total results: {total_results}")
    print(f"  Unique IDs: {len(unique_ids)}")
    print(f"  Diversity ratio: {diversity_ratio:.1%}")

    # Should have >50% unique (not same 6 IDs repeated)
    assert diversity_ratio > 0.5, f"Low diversity: {diversity_ratio:.1%}"

    # Even better: should have >70% unique
    assert diversity_ratio > 0.7, f"MMR not diverse enough: {diversity_ratio:.1%}"
```

---

## Implementation Checklist

### Phase 1: Implementation (4 hours)
- [ ] Fix #1: Update background task logging
  - [ ] Create new log_notification_safe function
  - [ ] Add logger setup with rotation
  - [ ] Update endpoint to use Pydantic validation
  - [ ] Time: 1.5 hours

- [ ] Fix #2: Update response model
  - [ ] Change truthiness check to explicit None check
  - [ ] Add response_with_tax model
  - [ ] Add validators for numeric fields
  - [ ] Time: 1 hour

- [ ] Fix #3: Adjust MMR diversity
  - [ ] Modify lambda_param in _retrieve_mmr
  - [ ] Or implement full diversity calculation
  - [ ] Time: 1.5 hours

### Phase 2: Testing (2 hours)
- [ ] Add test cases for each fix
- [ ] Run existing test suite (regression)
- [ ] Verify no breaking changes
- [ ] Time: 2 hours

### Phase 3: Validation (1 hour)
- [ ] Code review
- [ ] Re-run quality analyzer script
- [ ] Verify metrics improved
- [ ] Time: 1 hour

---

## Expected Outcomes

### After Implementation
| Metric | Before | After | Target |
|--------|--------|-------|--------|
| P0 Issues | 6 | 0 | 0 ✅ |
| Code Duplication | 96% | <30% | <20% |
| Quality Score | 96.7 | 98+ | 95+ |
| Test Coverage | 40% | 60% | 85% |

### Deployment
- Deploy to staging for 24-hour validation
- Monitor logs for errors
- Deploy to production with feature flag
- Monitor metrics post-deployment

---

**Estimated Total Time: 7-8 hours**
**Status: Ready for implementation**
**Priority: THIS WEEK**
