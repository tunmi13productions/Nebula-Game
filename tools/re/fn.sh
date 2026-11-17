# Prints every function whose header line matches the regex, from the Ghidra pseudocode dump.
# usage: bash tools/re/fn.sh '<regex>'   (run from the repository root)
awk -v pat="$1" '/^\/\/ ==== /{p = ($0 ~ pat)} p' decompiled/analysis/decompiled.c | grep -v '^\s*$'
