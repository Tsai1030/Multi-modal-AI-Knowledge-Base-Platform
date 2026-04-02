# Software Development Standards

## Overview

This document establishes unified standards for software development projects, aimed at improving code quality, maintainability, and team collaboration efficiency. All developers must strictly adhere to these standards in their development work.

---

## Project Architecture Standards

### Backend Architecture Principles
```
project_root/
├── api/
│   ├── main.py              # API main program (endpoint definitions only)
│   └── routers/             # Router module classification
├── src/                     # Core business logic
├── utils/                   # Common utility functions
├── model.py                 # Unified data model definitions
├── prompts.py               # Prompt template library
└── requirements.txt         # Dependency package list
```

### Frontend Architecture Principles
```
frontend/
├── components/              # UI components centralized management
├── pages/                   # Page files
├── utils/                   # Frontend utility functions
└── assets/                  # Static resources
```

---

## Code Organization Standards

### 1. API Design Guidelines

#### Separation of Concerns
- **API Main Program Responsibility**: Only responsible for endpoint routing definitions and application initialization
- **Business Logic Separation**: All business logic should be extracted to corresponding modules
- **No Mixing**: Main program must not contain any business processing functions

#### Endpoint Control
- **Allowed Endpoints**:
  - `/` - Application root path
  - `/health` - System health check
- **Prohibited Endpoints**: Testing, debugging, or development-specific endpoints
- **Router Grouping**: Use Router mechanism to group management by functional modules

### 2. Data Model Unification

#### Centralized Definition Principles
- **Unified File**: All data structure definitions centralized in `model.py`
- **Avoid Duplication**: Files are prohibited from duplicating the same data structure definitions
- **Standard References**: Uniformly use import method to reference data models

#### Implementation Example
```python
# model.py - Unified definitions
from pydantic import BaseModel

class StandardRequest(BaseModel):
    # Unified request format

class StandardResponse(BaseModel):
    # Unified response format

# Other files - Standard references
from model import StandardRequest, StandardResponse
```

### 3. Error Handling and Logging Standards

#### Conciseness Principles
- **Single Line Principle**: All logger and raise messages should be written in a single line
- **Complete Information**: Provide sufficient error information under the premise of conciseness
- **Unified Format**: Adopt consistent error message format
- **Fail Fast**: Include context for debugging; handle errors at the appropriate level; never silently swallow exceptions

#### Standard Format
```python
# Correct example
logger.error("Operation failed: reason description")
raise ValueError("Invalid input parameter")

# Avoid format
logger.error(
    "Operation failed because "
    "of multiple line description"
)
```

### 4. Code Modularity

#### Classification Principles
- **Utility Functions**: Common utility functions uniformly placed in `utils/` directory
- **Business Logic**: Core functional modules placed in `src/` or functional classification directories
- **Clear Division**: Avoid functional responsibility overlap
- **Shared Code**: Place code in shared modules only if used by ≥ 2 packages or modules

#### Function Quality Checklist
Before finalizing any function, verify:
1. Can you read the function and honestly easily follow what it's doing?
2. Does the function have very high cyclomatic complexity (excessive nesting / branching)?
3. Are there common data structures or algorithms that would make it cleaner?
4. Are there any unused parameters?
5. Are there unnecessary type casts that can be moved to function arguments?
6. Is the function easily testable without heavy mocking?
7. Does it have hidden untested dependencies that can be factored into arguments?
8. Brainstorm 3 better function names — confirm the current name is the best and consistent with the codebase.

> **IMPORTANT**: Do NOT extract a new function unless:
> - It will be reused in more than one place
> - It's the only way to unit-test otherwise untestable logic
> - The original function is extremely hard to follow without extensive comments

### 5. Prompt Management Standards

#### Centralized Management
- **Unified File**: Long prompts uniformly defined in `prompts.py`
- **Modularization**: Organize prompts by functional classification
- **Easy Maintenance**: Facilitate unified modification and version management

#### Usage Method
```python
# prompts.py
SYSTEM_PROMPT = """
Long prompt content...
"""

USER_PROMPT_TEMPLATE = """
User prompt template...
"""

# Main program reference
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
```

### 6. Frontend Organization Standards

#### Structural Principles
- **Avoid Over-segmentation**: Prohibit one directory containing only one file
- **Logical Grouping**: Related functional components should be appropriately categorized
- **Scalability**: Maintain structural flexibility to respond to requirement changes

---

## Development Philosophy and Process

### Core Philosophy

#### Fundamental Beliefs
- **Incremental progress over big bangs** - Small changes that compile and pass tests
- **Learning from existing code** - Study and plan before implementing
- **Pragmatic over dogmatic** - Adapt to project reality
- **Clear intent over clever code** - Choose boring and obvious solutions

#### Simplicity Definition
- Single responsibility per function/class
- Avoid premature abstractions
- No clever tricks - choose the boring solution
- If you need to explain it, it's too complex

### Development Process

#### 0. Before Coding (新增)
- **Ask clarifying questions** before starting complex work
- **Draft and confirm an approach** for non-trivial tasks
- **If ≥ 2 approaches exist**, list clear pros and cons before deciding

#### 1. Planning and Staging

Break complex work into 3-5 stages, documented in `IMPLEMENTATION_PLAN.md`:
```markdown
## Stage N: [Name]
**Goal**: [Specific deliverable]
**Success Criteria**: [Testable outcomes]
**Tests**: [Specific test cases]
**Status**: [Not Started|In Progress|Complete]
```

- Update status as you progress
- Remove file when all stages are done

#### 2. Implementation Flow

1. **Understand** - Study existing patterns in codebase; find 3 similar features and follow the same patterns
2. **Test** - Write test first (red) — scaffold stub → write failing test → implement
3. **Implement** - Minimal code to pass (green)
4. **Refactor** - Clean up with tests passing
5. **Commit** - With clear message linking to plan

#### 3. When Stuck (After 3 Attempts)

**CRITICAL**: Maximum 3 attempts per issue, then STOP.

1. **Document what failed**: what you tried, specific error messages, why you think it failed
2. **Research alternatives**: find 2–3 similar implementations and note different approaches
3. **Question fundamentals**: Is this the right abstraction level? Can this be split? Is there a simpler approach?
4. **Try different angle**: different library feature, different architectural pattern, or remove abstraction instead of adding

---

## Technical Standards

### Architecture Principles

- **Composition over inheritance** - Use dependency injection
- **Interfaces over singletons** - Enable testing and flexibility
- **Explicit over implicit** - Clear data flow and dependencies
- **Test-driven when possible** - Never disable tests, fix them

### Code Quality Standards

#### Every commit must:
- Compile successfully
- Pass all existing tests
- Include tests for new functionality
- Follow project formatting/linting

#### Before committing:
- Run formatters/linters
- Self-review changes
- Ensure commit message explains "why"

### Error Handling Principles

- Fail fast with descriptive messages
- Include context for debugging
- Handle errors at appropriate level
- Never silently swallow exceptions

---

## Testing Standards (新增完整章節)

### Testing Philosophy
- **TDD First**: scaffold stub → write failing test → implement (red → green → refactor)
- **Prefer integration tests** over heavy mocking
- **Separate concerns**: Always keep pure-logic unit tests separate from DB-touching integration tests
- **Test behavior, not implementation**

### Test Quality Checklist
1. Parameterize inputs; never embed unexplained literals (e.g. `42` or `"foo"`) directly in tests
2. Do not add a test unless it can fail for a real defect — trivial asserts are forbidden
3. Test description must state exactly what the final assertion verifies
4. Compare results to independently pre-computed expectations, never to the function's own output reused as oracle
5. Follow the same lint, type-safety, and style rules as production code
6. Express invariants or axioms (commutativity, idempotence, round-trip) rather than single hard-coded cases when practical
7. Group unit tests for a function under `describe(functionName, () => ...)`
8. Use strong assertions: `expect(x).toEqual(1)` instead of `expect(x).toBeGreaterThanOrEqual(1)`
9. Test edge cases, realistic input, unexpected input, and value boundaries
10. Do NOT test conditions already caught by the type checker

### Test Organization
- **Unit tests**: colocate in `*.spec.ts` (or equivalent) in the same directory as the source file
- **Integration tests**: place in a dedicated `test/` directory
- **One assertion per test** when possible; test the entire structure in one assertion if feasible:
```typescript
// ✅ Good
expect(result).toBe([value])

// ❌ Avoid
expect(result).toHaveLength(1);
expect(result[0]).toBe(value);
```

---

## Code Quality Standards

### Naming Conventions
- **File Naming**: Use snake_case format (backend); follow framework conventions for frontend
- **Descriptive Naming**: File and function names should clearly express functional purpose
- **Avoid Abbreviations**: Prioritize complete, clear vocabulary
- **Domain Vocabulary**: Name functions using existing domain vocabulary for consistency

### Import Order
1. Standard libraries
2. Third-party packages
3. Local modules

### Code Style
- Follow language standard specifications (e.g., Python PEP 8)
- Use meaningful variable and function names
- Appropriately comment complex logic sections — but **avoid comments for self-explanatory code**; rely on readable naming instead
- **No unnecessary comments**: only add comments for critical caveats or non-obvious decisions

---

## Git Standards (新增)

### Commit Message Format
Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0):
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Allowed types**: `fix`, `feat`, `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`

**Examples**:
- `feat(auth): add JWT refresh token support`
- `fix(api): handle null response from upstream service`
- `BREAKING CHANGE: rename endpoint /users to /accounts`

### Commit Rules
- **MUST** use Conventional Commits format
- **MUST NOT** refer to AI tools (Claude, Anthropic, etc.) in commit messages
- Every commit must compile, pass all tests, and follow formatting standards
- Commit message body should explain **why**, not just what

---

## Decision Framework

When multiple valid approaches exist, choose based on:

1. **Testability** - Can I easily test this?
2. **Readability** - Will someone understand this in 6 months?
3. **Consistency** - Does this match project patterns?
4. **Simplicity** - Is this the simplest solution that works?
5. **Reversibility** - How hard to change later?

---

## Project Integration

### Learning the Codebase

- Find 3 similar features/components before implementing
- Identify common patterns and conventions
- Use same libraries/utilities when possible
- Follow existing test patterns
- Use project's existing build system, test framework, and formatter/linter — don't introduce new tools without strong justification

---

## Quick Reference Shortcuts (新增)

These shortcuts can be invoked at any time during development:

### QPLAN
```
Analyze similar parts of the codebase and determine whether your plan:
- is consistent with the rest of the codebase
- introduces minimal changes
- reuses existing code
```

### QCHECK
```
Act as a skeptical senior software engineer.
Perform this analysis for every MAJOR code change introduced (skip minor changes):
1. Function Quality Checklist
2. Test Quality Checklist
3. Implementation Best Practices
```

### QCHECKF
```
Act as a skeptical senior software engineer.
For every MAJOR function added or edited, run through the Function Quality Checklist.
```

### QCHECKT
```
Act as a skeptical senior software engineer.
For every MAJOR test added or edited, run through the Test Quality Checklist.
```

### QUX
```
Imagine you are a human UX tester of the feature just implemented.
Output a comprehensive list of test scenarios sorted by highest priority.
```

### QGIT
```
Add all changes to staging, create a commit, and push to remote.
Follow the Git Standards section for commit message format.
```

---

## Compliance Checklist

### Architecture Check
- [ ] API main program contains only endpoint definitions
- [ ] Business logic appropriately separated to corresponding modules
- [ ] Use Router mechanism for grouped endpoint management

### Data Management Check
- [ ] All data models uniformly defined in `model.py`
- [ ] Modules use standard import method for references
- [ ] No duplicate definitions of the same data structure

### Code Quality Check
- [ ] Logger and raise messages comply with single-line principle
- [ ] Utility functions moved to `utils/` directory
- [ ] Long prompts extracted to `prompts.py`
- [ ] No unnecessary comments — code is self-explanatory

### Testing Check
- [ ] Tests written before implementation (TDD)
- [ ] Unit tests separated from integration tests
- [ ] No trivial or implementation-testing assertions
- [ ] Edge cases and boundary conditions covered

### Git Check
- [ ] Commit messages follow Conventional Commits format
- [ ] No AI tool references in commit messages
- [ ] Each commit compiles and passes all tests

### Security Check
- [ ] Only necessary API endpoints exposed
- [ ] No test or debug endpoints exposed
- [ ] Follow principle of least privilege

---

## Quality Gates

### Definition of Done

- [ ] Tests written and passing
- [ ] Code follows project conventions
- [ ] No linter/formatter warnings
- [ ] Commit messages are clear and follow Conventional Commits
- [ ] Implementation matches plan
- [ ] No TODOs without issue numbers

---

## Important Reminders

### NEVER:
- Use `--no-verify` to bypass commit hooks
- Disable tests instead of fixing them
- Commit code that doesn't compile
- Make assumptions — verify with existing code
- Add comments that just restate what the code does
- Refer to Claude or other AI tools in commit messages
- Introduce new tools/libraries without strong justification

### ALWAYS:
- Commit working code incrementally
- Update plan documentation as you go
- Learn from existing implementations
- Stop after 3 failed attempts and reassess
- Ask clarifying questions before starting complex work

---

## Version Management

- **Version**: v1.2
- **Effective Date**: [Establishment Date]
- **Scope**: All software development projects
- **Update Cycle**: Rolling revisions as needed

---

**Important Notice**: This specification is a mandatory enforcement standard, and all developers must strictly comply. For questions or suggestions, please submit revision requests through official channels.