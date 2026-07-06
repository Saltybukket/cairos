# CAIROS bash integration
# Source this file in ~/.bashrc:
#   source /path/to/cairos/integrations/cairos.bash

_cairos_expand_command() {
  local expanded
  expanded=$(cairos expand $READLINE_LINE 2>/dev/null)
  if [[ -n "$expanded" ]]; then
    READLINE_LINE="$expanded"
    READLINE_POINT=${#READLINE_LINE}
  fi
}

bind -x '"\C-g": _cairos_expand_command'
