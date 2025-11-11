# Phase 7: Human Review (Optional)

**Document**: 09 of 15
**Purpose**: Smart human-in-the-loop for 99%+ precision

---

## Overview

**Phase 7 is OPTIONAL** - enables 99%+ precision through selective human review.

**Key Innovation**: Review only 15-20% lowest-confidence atoms, not all 800

**Result**: 98% autonomous → 99%+ with human collaboration

---

## Why Optional Human Review?

```
Fully Autonomous (Phase 6 only):
- 95-98% precision
- 1-1.5 hours execution
- $180 cost
- ✅ Best-in-class without human input

With Human Review (Phase 7):
- 99%+ precision
- 1.5-2 hours execution (+ 20-30 min human review)
- $280-330 cost
- ✅ Near-perfect output with minimal human effort
```

---

## Confidence Scoring

### Algorithm

```python
class ConfidenceScorer:
    """Calculate confidence scores for atoms."""
    
    def calculate_confidence(
        self,
        atom: AtomicUnit,
        validation_result: AtomicValidationResult,
        execution_result: ExecutionResult
    ) -> float:
        """
        Calculate confidence score (0.0 - 1.0).
        
        Factors:
        1. Validation score (40%)
        2. Attempts needed (30%)
        3. Complexity (15%)
        4. Context completeness (15%)
        """
        
        # 1. Validation score (40%)
        validation_score = validation_result.score * 0.40
        
        # 2. Attempts (30%)
        # Fewer attempts = higher confidence
        attempt_score = (1.0 - (execution_result.attempts - 1) / 3) * 0.30
        
        # 3. Complexity (15%)
        # Lower complexity = higher confidence
        complexity_score = max(0, 1.0 - atom.complexity / 5) * 0.15
        
        # 4. Context completeness (15%)
        context_score = atom.context.get('completeness_score', 0.7) * 0.15
        
        total_confidence = (
            validation_score +
            attempt_score +
            complexity_score +
            context_score
        )
        
        return min(1.0, max(0.0, total_confidence))
```

### Confidence Thresholds

```python
CONFIDENCE_THRESHOLDS = {
    'high': 0.90,      # No review needed (80-85% of atoms)
    'medium': 0.75,    # Optional review (10-15% of atoms)
    'low': 0.60,       # Review recommended (5-10% of atoms)
    'critical': 0.50   # Must review (<5% of atoms)
}

def should_flag_for_review(confidence: float) -> bool:
    """Flag atoms below medium confidence."""
    return confidence < CONFIDENCE_THRESHOLDS['medium']
```

---

## Review Interface

### UI Components

```typescript
// React component for review interface

interface AtomReviewProps {
  atom: AtomicUnit;
  confidence: number;
  validationIssues: ValidationIssue[];
  dependencies: AtomicUnit[];
}

function AtomReview({ atom, confidence, validationIssues, dependencies }: AtomReviewProps) {
  const [action, setAction] = useState<'approve' | 'edit' | 'regenerate'>(null);
  const [editedCode, setEditedCode] = useState(atom.code);
  const [feedback, setFeedback] = useState('');
  
  return (
    <div className="atom-review-card">
      {/* Confidence Badge */}
      <ConfidenceBadge score={confidence} />
      
      {/* Atom Info */}
      <div className="atom-info">
        <h3>{atom.name}</h3>
        <p>{atom.description}</p>
        <p>Complexity: {atom.complexity} | LOC: {atom.estimated_loc}</p>
      </div>
      
      {/* Validation Issues */}
      {validationIssues.length > 0 && (
        <ValidationIssues issues={validationIssues} />
      )}
      
      {/* Code Editor */}
      <CodeEditor
        code={editedCode}
        language={atom.language}
        onChange={setEditedCode}
        readOnly={action !== 'edit'}
      />
      
      {/* Dependencies Context */}
      <DependenciesPanel dependencies={dependencies} />
      
      {/* AI Suggestions */}
      <AISuggestions atom={atom} issues={validationIssues} />
      
      {/* Actions */}
      <div className="review-actions">
        <button onClick={() => handleApprove()}>✅ Approve</button>
        <button onClick={() => setAction('edit')}>✏️ Edit</button>
        <button onClick={() => handleRegenerate()}>🔄 Regenerate</button>
      </div>
      
      {/* Feedback */}
      <textarea
        placeholder="Optional feedback for regeneration..."
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
      />
    </div>
  );
}
```

### Workflow

```python
class HumanReviewWorkflow:
    """Manage human review workflow."""
    
    def create_review_queue(
        self,
        atoms: List[AtomicUnit],
        execution_results: Dict[str, ExecutionResult],
        validation_results: Dict[str, AtomicValidationResult]
    ) -> List[ReviewItem]:
        """Create prioritized review queue."""
        
        scorer = ConfidenceScorer()
        review_queue = []
        
        for atom in atoms:
            exec_result = execution_results.get(atom.id)
            val_result = validation_results.get(atom.id)
            
            if not exec_result or not val_result:
                continue
            
            # Calculate confidence
            confidence = scorer.calculate_confidence(atom, val_result, exec_result)
            
            # Flag for review if low confidence
            if should_flag_for_review(confidence):
                review_queue.append(ReviewItem(
                    atom=atom,
                    confidence=confidence,
                    validation_issues=val_result.issues,
                    priority=self._calculate_priority(confidence, val_result)
                ))
        
        # Sort by priority (lowest confidence first)
        review_queue.sort(key=lambda x: x.confidence)
        
        return review_queue
    
    def _calculate_priority(
        self,
        confidence: float,
        validation: AtomicValidationResult
    ) -> int:
        """
        Calculate review priority (higher = more urgent).
        
        1-5 scale based on confidence and criticality.
        """
        if confidence < 0.50:
            return 5  # Critical
        elif confidence < 0.60:
            return 4  # High
        elif confidence < 0.70:
            return 3  # Medium
        elif confidence < 0.80:
            return 2  # Low
        else:
            return 1  # Minimal
```

---

## AI-Assisted Review

### Smart Suggestions

```python
class ReviewAssistant:
    """AI assistant for human reviewers."""
    
    def generate_suggestions(
        self,
        atom: AtomicUnit,
        validation_issues: List[ValidationIssue]
    ) -> List[Suggestion]:
        """Generate AI suggestions for fixes."""
        
        suggestions = []
        
        for issue in validation_issues:
            if issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]:
                # Generate fix suggestion using LLM
                suggestion = self._generate_fix_suggestion(atom, issue)
                suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_fix_suggestion(
        self,
        atom: AtomicUnit,
        issue: ValidationIssue
    ) -> Suggestion:
        """Use LLM to suggest fix."""
        
        prompt = f"""
The following code has an issue:

**Code**:
```{atom.language}
{atom.code}
```

**Issue**: {issue.message} (Category: {issue.category}, Severity: {issue.severity.value})

Suggest a fix. Provide:
1. Brief explanation of the issue
2. Corrected code
3. Why this fix solves the problem
"""
        
        # Call Claude for suggestion
        response = self.llm_client.generate(prompt)
        
        return Suggestion(
            issue=issue,
            explanation=response['explanation'],
            fixed_code=response['fixed_code'],
            rationale=response['rationale']
        )
```

---

## Review Analytics

### Metrics Tracking

```python
@dataclass
class ReviewMetrics:
    """Track review session metrics."""
    
    total_flagged: int
    total_reviewed: int
    approved: int
    edited: int
    regenerated: int
    avg_review_time: float  # seconds per atom
    precision_before: float
    precision_after: float

class ReviewAnalytics:
    """Track and report review analytics."""
    
    def calculate_metrics(
        self,
        review_session: ReviewSession
    ) -> ReviewMetrics:
        """Calculate review session metrics."""
        
        return ReviewMetrics(
            total_flagged=len(review_session.flagged_atoms),
            total_reviewed=len(review_session.reviewed_atoms),
            approved=len([a for a in review_session.actions if a == 'approve']),
            edited=len([a for a in review_session.actions if a == 'edit']),
            regenerated=len([a for a in review_session.actions if a == 'regenerate']),
            avg_review_time=review_session.total_time / len(review_session.reviewed_atoms),
            precision_before=review_session.precision_before_review,
            precision_after=review_session.precision_after_review
        )
```

---

## Performance Metrics

| Metric | Target | Typical |
|--------|--------|---------|
| **Atoms flagged** | 15-20% | 120-160 atoms |
| **Review time per atom** | 10-15s | 12s |
| **Total review time** | 20-30 min | 24 min |
| **Approval rate** | 60-70% | 65% |
| **Edit rate** | 20-25% | 22% |
| **Regeneration rate** | 10-15% | 13% |
| **Precision improvement** | 98% → 99%+ | 98.2% → 99.4% |

---

## Cost-Benefit Analysis

```
Autonomous Only (Phase 6):
- Precision: 98%
- Time: 1.5 hours
- Cost: $180
- Failures: 16/800 atoms (2%)

With Human Review (Phase 7):
- Precision: 99.4%
- Time: 1.5h + 24min = 1.9 hours
- Cost: $330 ($180 + $150 human time)
- Failures: 5/800 atoms (0.6%)

ROI Analysis:
- Additional cost: $150
- Failures reduced: 11 atoms (from 16 to 5)
- Cost per failure prevented: $13.64
- Time to fix failures manually: ~30 min each = 5.5 hours saved
- Net benefit: 5.5 hours - 0.4 hours = 5.1 hours saved ✅
```

---

**Next Document**: [10_INTEGRATION_DEVMATRIX.md](10_INTEGRATION_DEVMATRIX.md)
