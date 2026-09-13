return {
  'mfussenegger/nvim-dap-python',
  ft = 'python',
  dependencies = { 'mfussenegger/nvim-dap' },
  config = function()
    local python = vim.fn.expand '~/miniconda3/envs/py310/bin/python'
    require('dap-python').setup(python)
  end,
}
