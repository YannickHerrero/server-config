return {
  "echasnovski/mini.nvim",
  version = "*",
  event = "VeryLazy",
  config = function()
    require("mini.pairs").setup()
    require("mini.surround").setup()
    require("mini.icons").setup()
    require("mini.statusline").setup({ use_icons = true })
    require("mini.tabline").setup()

    local function set_current_tab_hl()
      vim.api.nvim_set_hl(0, "MiniTablineCurrent", {
        ctermbg = "NONE",
        ctermfg = "NONE",
        cterm = { bold = true, reverse = true },
      })
      vim.api.nvim_set_hl(0, "MiniTablineModifiedCurrent", {
        ctermbg = "NONE",
        ctermfg = "NONE",
        cterm = { bold = true, reverse = true, italic = true },
      })
    end

    set_current_tab_hl()
    vim.api.nvim_create_autocmd("ColorScheme", {
      group = vim.api.nvim_create_augroup("tabline-current-hl", { clear = true }),
      callback = set_current_tab_hl,
    })
  end,
}
