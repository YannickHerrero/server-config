return {
  "folke/which-key.nvim",
  tag = "v3.17.0",
  event = "VeryLazy",
  opts = {
    plugins = { spelling = true },
    spec = {
      {
        mode = { "n", "v" },
        { "<leader>b", group = "buffer" },
        { "<leader>f", group = "file/find" },
        { "<leader>s", group = "search" },
      },
    },
  },
}
