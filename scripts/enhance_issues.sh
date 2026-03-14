#!/bin/bash
# Enhanced issue analyzer - revises GitHub issues with code context and fix suggestions
# Runs every 15 minutes

REPO="rohannagpure45/RohanNagpureACMHackathon2"
REPO_DIR="/home/ubuntu/.openclaw/workspace/RohanNagpureACMHackathon2"

cd "$REPO_DIR" || exit 1

echo "=== Enhanced Issue Analysis ==="
echo "Date: $(date)"
echo ""

# Get all open issues
ISSUES=$(gh issue list --repo "$REPO" --state open --json number,title 2>/dev/null)

if [ -z "$ISSUES" ]; then
    echo "No open issues found"
    exit 0
fi

echo "$ISSUES" | jq -r '.[] | "\(.number)"' | while read issue_num; do
    echo "--- Analyzing Issue #$issue_num ---"
    
    # Get issue title and body
    ISSUE_DATA=$(gh issue view "$issue_num" --repo "$REPO" --json title,body 2>/dev/null)
    TITLE=$(echo "$ISSUE_DATA" | jq -r '.title')
    BODY=$(echo "$ISSUE_DATA" | jq -r '.body // empty')
    
    echo "Title: $TITLE"
    
    # Analyze based on issue type
    ENHANCED_BODY="$BODY"
    
    case "$TITLE" in
        *"Type mismatch"*)
            # Find the actual type definitions in the codebase
            echo "Analyzing type mismatch..."
            
            # Extract type names from title
            if echo "$TITLE" | grep -q "Session.id"; then
                BACKEND_TYPE=$(grep -A1 "class SessionResponse" backend/api/schemas.py 2>/dev/null | grep "id:" | xargs)
                FRONTEND_TYPE=$(grep -A2 "export interface Session" frontend/src/types/index.ts 2>/dev/null | head -3)
                ENHANCED_BODY="$BODY

### Code Context (from codebase):
**Backend (schemas.py):**
\`\`\`
$BACKEND_TYPE
\`\`\`

**Frontend (types/index.ts):**
\`\`\`
$FRONTEND_TYPE
\`\`\`

### Suggested Fix:
The frontend type should match the backend Pydantic model which uses \`int\` for the id field."
            fi
            ;;
        *"Hardcoded"*|*"localhost"*)
            echo "Analyzing hardcoded URLs..."
            # Check for other hardcoded URLs
            HARDCODE_COUNT=$(grep -r "localhost:8000\|127.0.0.1:8000" frontend/src --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l)
            ENHANCED_BODY="$BODY

### Additional Analysis:
Found $HARDCODE_COUNT occurrences of hardcoded localhost URLs in frontend.

### Suggested Fix Approach:
1. Create .env file with VITE_API_URL
2. Replace hardcoded URLs with \`import.meta.env.VITE_API_URL\`
3. Add fallback to localhost for development"
            ;;
        *)
            echo "Generic issue - adding codebase context..."
            # Add general context
            FILE_COUNT=$(find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) | wc -l)
            ENHANCED_BODY="$BODY

### Codebase Statistics:
- Total source files: $FILE_COUNT
- Backend Python files: $(find backend -name "*.py" 2>/dev/null | wc -l)
- Frontend TS/TSX files: $(find frontend/src -name "*.ts" -o -name "*.tsx" 2>/dev/null | wc -l)"
            ;;
    esac
    
    # Update issue with enhanced body if different
    if [ "$ENHANCED_BODY" != "$BODY" ]; then
        echo "Updating issue #$issue_num with enhanced context..."
        gh issue edit "$issue_num" --body "$ENHANCED_BODY" --repo "$REPO" 2>/dev/null
        echo "Updated!"
    else
        echo "No enhancement needed"
    fi
    
    echo ""
done

echo "=== Analysis Complete ==="
