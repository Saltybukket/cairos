# CAIROS fish integration
# Source this file in ~/.config/fish/config.fish:
#   source /path/to/cairos/integrations/cairos.fish

function cairos_expand_command
    set current (commandline)
    set expanded (cairos expand $current 2>/dev/null)
    if test -n "$expanded"
        commandline -r "$expanded"
    end
end

bind \cg cairos_expand_command
