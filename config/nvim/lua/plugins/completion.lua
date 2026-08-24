return {
  "saghen/blink.cmp",
  version = "1.*",
  event = "InsertEnter",
  opts = {
    keymap = {
      preset = "default",
      ["<CR>"] = { "accept", "fallback" },
      ["<C-n>"] = { "select_next", "fallback" },
      ["<C-p>"] = { "select_prev", "fallback" },
      ["<C-Space>"] = { "show", "show_documentation", "hide_documentation" },
    },
    sources = {
      default = { "lsp", "path", "buffer" },
    },
    completion = {
      documentation = { auto_show = true, auto_show_delay_ms = 200 },
    },
    signature = { enabled = true },
  },
}
