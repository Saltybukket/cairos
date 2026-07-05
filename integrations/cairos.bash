# CAIROS bash integration
# Usage: source integrations/cairos.bash

_cairos_expand_command() {
    local expanded
    expanded=$(cairos expand "$READLINE_LINE" 2>/tmp/cairos-expand-error)
    if [[ $? -eq 0 ]]; then
        READLINE_LINE="$expanded"
        READLINE_POINT=${#READLINE_LINE}
    fi
}

bind -x '"\C-g": _cairos_expand_command'
