HISTSIZE=5000
SAVEHIST=$HISTSIZE
HISTFILE="${XDG_STATE_HOME:-$HOME/.local/state}/zsh/history"
HISTDUP=erase

setopt appendhistory
setopt sharehistory
setopt hist_ignore_space
setopt hist_ignore_all_dups
setopt hist_save_no_dups
setopt hist_ignore_dups
setopt hist_find_no_dups

autoload -Uz history-search-end
zle -N history-beginning-search-backward-end history-search-end
zle -N history-beginning-search-forward-end history-search-end
[[ -n ${terminfo[kcuu1]:-} ]] && \
    bindkey "$terminfo[kcuu1]" history-beginning-search-backward-end
[[ -n ${terminfo[kcud1]:-} ]] && \
    bindkey "$terminfo[kcud1]" history-beginning-search-forward-end
