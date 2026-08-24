if command -v mise >/dev/null 2>&1; then
    eval "$(mise activate zsh)"
fi

if command -v oh-my-posh >/dev/null 2>&1; then
    eval "$(oh-my-posh init zsh --config "$HOME/.config/ohmyposh/zen.toml")"
fi

if command -v zoxide >/dev/null 2>&1; then
    eval "$(zoxide init --cmd z zsh)"
fi
