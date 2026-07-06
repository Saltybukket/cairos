# CAIROS zsh integration
# Source this file in ~/.zshrc:
#   source /path/to/cairos/integrations/cairos.zsh

cairos-expand-command() {
  local expanded
  expanded=$(cairos expand ${(z)BUFFER} 2>/dev/null)
  if [[ -n "$expanded" ]]; then
    BUFFER="$expanded"
    CURSOR=${#BUFFER}
  else
    zle -M "CAIROS: no deterministic expansion matched"
  fi
}

zle -N cairos-expand-command
bindkey '^G' cairos-expand-command
