# CAIROS fish integration
# Usage: source integrations/cairos.fish

function cairos_expand_command
    set current (commandline)
    set expanded (cairos expand "$current" 2>/tmp/cairos-expand-error)
    if test $status -eq 0
        commandline -r "$expanded"
    end
end

bind \cg cairos_expand_command
