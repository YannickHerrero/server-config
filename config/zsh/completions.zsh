zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'
zstyle ':completion:*' menu no

if [[ -n ${LS_COLORS:-} ]]; then
    zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"
fi

zstyle ':fzf-tab:complete:cd:*' fzf-preview \
    'eza --tree --level=1 --color=always "$realpath"'
zstyle ':fzf-tab:complete:__zoxide_z:*' fzf-preview \
    'eza --tree --level=1 --color=always "$realpath"'
