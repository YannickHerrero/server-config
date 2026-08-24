ff() {
    local file
    file=$(find "$HOME/dev" "$HOME/.config" \
        -type d \( \
            -name .git -o \
            -name .cache -o \
            -name .next -o \
            -name .npm -o \
            -name .venv -o \
            -name build -o \
            -name coverage -o \
            -name dist -o \
            -name node_modules -o \
            -name vendor \
        \) -prune -o -type f -print 2>/dev/null | \
        fzf \
            --preview 'bat --color=always --style=numbers --line-range=:500 {}' \
            --bind 'ctrl-d:preview-half-page-down,ctrl-u:preview-half-page-up')

    [[ -n $file ]] && nvim "$file"
}
