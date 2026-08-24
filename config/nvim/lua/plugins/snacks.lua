return {
  "folke/snacks.nvim",
  priority = 1000,
  lazy = false,
  opts = {
    picker = {
      enabled = true,
      sources = {
        explorer = {
          layout = { layout = { position = "right" } },
          jump = { close = true },
        },
      },
    },
    explorer = { enabled = true },
    bigfile = { enabled = true },
    quickfile = { enabled = true },
    dashboard = {
      sections = {
        { section = "header" },
        { section = "keys", gap = 1, padding = 1 },
        {
          icon = " ",
          desc = "Browse repository",
          key = "b",
          action = function()
            Snacks.gitbrowse()
          end,
        },
        { section = "startup" },
      },
    },
  },
  keys = {
    { "<leader> ", function() Snacks.picker.files() end, desc = "find file" },
    { "<leader>sg", function() Snacks.picker.grep() end, desc = "live grep" },
    { "<leader>e", function() Snacks.explorer() end, desc = "file explorer" },
  },
}
