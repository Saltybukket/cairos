# CAIROS zsh integration
# Usage: source integrations/cairos.zsh
# Type natural language, press Ctrl+G, inspect expansion, press Enter.

cairos-expand-command() {
    local expanded
    expanded=$(cairos expand "$BUFFER" 2>/tmp/cairos-expand-error)
    if [[ $? -eq 0 ]]; then
        BUFFER="$expanded"
        CURSOR=${#BUFFER}
    else
        zle -M "CAIROS could not expand this input"
    fi
}

zle -N cairos-expand-command
bindkey '^G' cairos-expand-command
