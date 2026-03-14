#!/bin/bash
# Auto-fix script - attempts to fix GitHub issues automatically
# Runs every 15 minutes after enhance_issues.sh

REPO="rohannagpure45/RohanNagpureACMHackathon2"
REPO_DIR="/home/ubuntu/.openclaw/workspace/RohanNagpureACMHackathon2"
BRANCH="bug-fixes"

cd "$REPO_DIR" || exit 1

echo "=== Auto-Fix Runner ==="
echo "Date: $(date)"
echo ""

# Check if there are uncommitted changes
if ! git diff --quiet || [ -n "$(git status --porcelain)" ]; then
    echo "Uncommitted changes exist. Please commit or stash them first."
    exit 1
fi

# Ensure we're on bug-fixes branch and up to date
git checkout "$BRANCH" 2>/dev/null
git pull origin "$BRANCH" 2>/dev/null

# Get open issues
ISSUES=$(gh issue list --repo "$REPO" --state open --json number,title 2>/dev/null)

if [ -z "$ISSUES" ]; then
    echo "No open issues to fix"
    exit 0
fi

echo "$ISSUES" | jq -r '.[] | "\(.number)|\(.title)"' | while read issue_line; do
    IFS='|' read -r issue_num title <<< "$issue_line"
    echo "--- Attempting to fix Issue #$issue_num: $title ---"
    
    # Check if issue is already fixed (closed)
    STATE=$(gh issue view "$issue_num" --repo "$REPO" --json state 2>/dev/null | jq -r '.state')
    if [ "$STATE" != "OPEN" ]; then
        echo "Issue #$issue_num is already $STATE, skipping"
        echo ""
        continue
    fi
    
    FIXED=0
    
    case "$title" in
        *"Type mismatch"*|"session_id"*)
            if echo "$title" | grep -q "Session.id"; then
                # Check if already fixed
                if grep -q "id: number" frontend/src/types/index.ts 2>/dev/null; then
                    echo "Session.id already fixed"
                else
                    sed -i 's/id: string/id: number/' frontend/src/types/index.ts
                    git add frontend/src/types/index.ts
                    git commit -m "Fix: Session.id type from string to number

Auto-fix for issue #$issue_num"
                    FIXED=1
                fi
            elif echo "$title" | grep -q "session_id"; then
                if grep -q "session_id: number" frontend/src/types/index.ts 2>/dev/null; then
                    echo "session_id already fixed"
                else
                    sed -i 's/session_id: string/session_id: number/' frontend/src/types/index.ts
                    git add frontend/src/types/index.ts
                    git commit -m "Fix: session_id type from string to number

Auto-fix for issue #$issue_num"
                    FIXED=1
                fi
            fi
            ;;
        *"Hardcoded"*|*"localhost"*)
            # Check if already has env var support
            if grep -q "import.meta.env.VITE_API_URL" frontend/src/components/Dashboard.tsx 2>/dev/null; then
                echo "Environment variable support already added"
            else
                # Add env var to each file
                for file in frontend/src/components/Dashboard.tsx frontend/src/components/UploadForm.tsx frontend/src/hooks/useSessionData.ts; do
                    if [ -f "$file" ] && grep -q "localhost:8000" "$file"; then
                        sed -i "s|http://localhost:8000|\${import.meta.env.VITE_API_URL || 'http://localhost:8000'}|g" "$file"
                        git add "$file"
                    fi
                done
                
                # Create .env.example if it doesn't exist
                if [ ! -f frontend/.env.example ]; then
                    echo "VITE_API_URL=http://localhost:8000/" > frontend/.env.example
                    git add frontend/.env.example
                fi
                
                if ! git diff --quiet --cached; then
                    git commit -m "Fix: Use environment variable for API URL

Auto-fix for issue #$issue_num"
                    FIXED=1
                fi
            fi
            ;;
        *)
            echo "No auto-fix available for this issue type"
            ;;
    esac
    
    if [ $FIXED -eq 1 ]; then
        echo "Changes committed, pushing to $BRANCH..."
        git push origin "$BRANCH" 2>/dev/null
        
        # Close the issue
        echo "Closing issue #$issue_num..."
        gh issue close "$issue_num" --repo "$REPO" 2>/dev/null
        echo "Issue #$issue_num fixed and closed!"
    else
        echo "No changes made for issue #$issue_num"
    fi
    
    echo ""
done

echo "=== Auto-Fix Complete ==="

# Show current status
echo ""
echo "Commits on $BRANCH:"
git log --oneline -5 origin/"$BRANCH" 2>/dev/null || git log --oneline -5
