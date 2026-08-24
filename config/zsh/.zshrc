plugin_root="$HOME/.local/share/server-config/zsh-plugins"
cache_root="${XDG_CACHE_HOME:-$HOME/.cache}/zsh"

fpath=("$plugin_root/zsh-completions/src" $fpath)
autoload -Uz compinit
compinit -d "$cache_root/zcompdump"

[[ -r "$plugin_root/zsh-autosuggestions/zsh-autosuggestions.zsh" ]] && \
    source "$plugin_root/zsh-autosuggestions/zsh-autosuggestions.zsh"
[[ -r "$plugin_root/fzf-tab/fzf-tab.plugin.zsh" ]] && \
    source "$plugin_root/fzf-tab/fzf-tab.plugin.zsh"

for config in "${ZDOTDIR:-$HOME/.config/zsh}"/*.zsh(N); do
    source "$config"
done

# Syntax highlighting must load after widgets and other shell configuration.
[[ -r "$plugin_root/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh" ]] && \
    source "$plugin_root/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
