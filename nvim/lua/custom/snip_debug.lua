vim.api.nvim_create_user_command('SnipDebug', function()
  local ls = require 'luasnip'

  print('ft:', vim.bo.filetype)
  print('autosnippets:', ls.session.config.enable_autosnippets)
  print('expandable:', ls.expandable())
  print('jumpable:', ls.jumpable and ls.jumpable(1) or 'no jumpable')
  print('in_snippet:', ls.session.current_nodes[vim.api.nvim_get_current_buf()] ~= nil)
  print('current_snippet:', ls.session.current_nodes[vim.api.nvim_get_current_buf()])
  print('in_mathzone:', vim.fn.exists '*vimtex#syntax#in_mathzone' == 1 and vim.fn['vimtex#syntax#in_mathzone']() or 'vimtex missing')
end, {})
