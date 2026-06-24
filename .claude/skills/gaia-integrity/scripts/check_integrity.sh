#!/bin/bash

# Gaia Registry Integrity Checker

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Starting Registry Integrity Check..."

# 1. Canonical Validation
echo -e "\n${YELLOW}[1/3] Running gaia validate...${NC}"
if gaia validate; then
    echo -e "${GREEN}✓ Canonical validation passed.${NC}"
else
    echo -e "${RED}✗ Canonical validation failed.${NC}"
fi

# 2. Documentation Alignment
echo -e "\n${YELLOW}[2/3] Checking Documentation Alignment...${NC}"
MISSING_DOCS=0
for node in $(find registry/nodes -name "*.json"); do
    # Extract type and id from path: registry/nodes/{type}/{id}.json
    REL_PATH=${node#registry/nodes/}
    TYPE=$(echo $REL_PATH | cut -d'/' -f1)
    ID=$(basename $REL_PATH .json)
    
    DOC_PATH="registry/skills/$TYPE/$ID.md"
    if [ ! -f "$DOC_PATH" ]; then
        echo -e "${RED}✗ Missing documentation for node: $ID ($TYPE)${NC}"
        echo "  Expected: $DOC_PATH"
        MISSING_DOCS=$((MISSING_DOCS + 1))
    fi
done

if [ $MISSING_DOCS -eq 0 ]; then
    echo -e "${GREEN}✓ All nodes have corresponding documentation.${NC}"
else
    echo -e "${RED}✗ Found $MISSING_DOCS nodes missing documentation.${NC}"
fi

# 3. Orphan Documentation
echo -e "\n${YELLOW}[3/3] Checking for Orphan Documentation...${NC}"
ORPHAN_DOCS=0
for doc in $(find registry/skills -name "*.md"); do
    REL_PATH=${doc#registry/skills/}
    TYPE=$(echo $REL_PATH | cut -d'/' -f1)
    ID=$(basename $REL_PATH .md)
    
    # Ignore suite documentation or special files if necessary
    if [[ "$ID" == "skills" ]] || [[ "$ID" == "setup-"* ]]; then
        continue
    fi

    NODE_PATH="registry/nodes/$TYPE/$ID.json"
    if [ ! -f "$NODE_PATH" ]; then
        echo -e "${YELLOW}! Orphan documentation found: $ID ($TYPE)${NC}"
        echo "  No matching node at: $NODE_PATH"
        ORPHAN_DOCS=$((ORPHAN_DOCS + 1))
    fi
done

if [ $ORPHAN_DOCS -eq 0 ]; then
    echo -e "${GREEN}✓ No orphan documentation found.${NC}"
else
    echo -e "${YELLOW}! Found $ORPHAN_DOCS orphan documentation files.${NC}"
fi

echo -e "\n🏁 Integrity Check Complete."
