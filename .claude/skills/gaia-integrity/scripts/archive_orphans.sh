#!/bin/bash

# Gaia Registry Archive Utility
# Archives orphan documentation files to registry/archive/

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ARCHIVE_DIR="registry/archive"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEST_ROOT="$ARCHIVE_DIR/$TIMESTAMP"

mkdir -p "$DEST_ROOT"

echo -e "${YELLOW}📦 Archiving orphan documentation to $DEST_ROOT...${NC}"

ORPHANS_FOUND=0
ARCHIVED_COUNT=0

for doc in $(find registry/skills -name "*.md"); do
    REL_PATH=${doc#registry/skills/}
    TYPE=$(echo $REL_PATH | cut -d'/' -f1)
    ID=$(basename $REL_PATH .md)
    
    # Ignore suite documentation or special files
    if [[ "$ID" == "skills" ]] || [[ "$ID" == "setup-"* ]]; then
        continue
    fi

    NODE_PATH="registry/nodes/$TYPE/$ID.json"
    if [ ! -f "$NODE_PATH" ]; then
        ORPHANS_FOUND=$((ORPHANS_FOUND + 1))
        
        # Create sub-directory in archive
        mkdir -p "$DEST_ROOT/$TYPE"
        
        # Move the file
        mv "$doc" "$DEST_ROOT/$TYPE/"
        echo -e "${YELLOW}  Moved: $REL_PATH${NC}"
        ARCHIVED_COUNT=$((ARCHIVED_COUNT + 1))
    fi
done

if [ $ARCHIVED_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ No orphans found to archive.${NC}"
    rmdir "$DEST_ROOT" 2>/dev/null
    rmdir "$ARCHIVE_DIR/$TIMESTAMP" 2>/dev/null
else
    echo -e "\n${GREEN}✓ Archived $ARCHIVED_COUNT files to $DEST_ROOT${NC}"
    echo -e "${YELLOW}Note: You may need to run 'gaia docs build' if these files were part of the generated graph.${NC}"
fi
