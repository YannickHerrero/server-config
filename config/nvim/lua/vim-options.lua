vim.g.mapleader = " "

local opt = vim.opt

if not vim.env.SSH_CONNECTION and vim.fn.has("clipboard") == 1 then
  opt.clipboard = "unnamedplus"
end

opt.completeopt = "menu,menuone,noselect"
opt.confirm = true
opt.cursorline = true
opt.expandtab = true
opt.fillchars = { eob = " " }
opt.laststatus = 0
opt.list = true
opt.mouse = "a"
opt.number = true
opt.relativenumber = true
opt.shiftwidth = 2
opt.showmode = false
opt.smartcase = true
opt.smartindent = true
opt.softtabstop = 2
opt.splitbelow = true
opt.splitright = true
opt.tabstop = 2
opt.undofile = true
opt.undolevels = 10000
opt.wrap = true
opt.scrolloff = 999
opt.sidescrolloff = 8

vim.diagnostic.config({
  signs = {
    text = {
      [vim.diagnostic.severity.ERROR] = "▎",
      [vim.diagnostic.severity.WARN] = "▎",
      [vim.diagnostic.severity.HINT] = "▎",
      [vim.diagnostic.severity.INFO] = "▎",
    },
  },
})

vim.keymap.set("n", "<leader>bd", "<cmd>bdelete<CR>", { desc = "close buffer" })
vim.keymap.set("n", "<S-h>", "<cmd>bprevious<CR>", { desc = "previous buffer" })
vim.keymap.set("n", "<S-l>", "<cmd>bnext<CR>", { desc = "next buffer" })
vim.keymap.set("n", "<leader>o", function()
  vim.opt.laststatus = vim.o.laststatus == 0 and 3 or 0
end, { desc = "toggle statusline" })
