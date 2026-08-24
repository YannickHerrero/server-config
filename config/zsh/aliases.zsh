alias v='nvim'
alias ..='cd ..'
alias ...='cd ../..'
alias ....='cd ../../..'
alias ls='eza --group-directories-first --color=auto'
alias ll='eza --long --all --group-directories-first --color=auto'
alias vswap='rm -rf "${XDG_STATE_HOME:-$HOME/.local/state}/nvim/swap"'

mkcd() {
    mkdir -p -- "$1" && cd -- "$1"
}
