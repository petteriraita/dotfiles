return {
  'mfussenegger/nvim-dap-python',
  ft = 'python',
  dependencies = { 'mfussenegger/nvim-dap' },
  config = function()
    local python = vim.fn.expand '~/miniconda3/envs/py310/bin/python'
    require('dap-python').setup(python)

    local dap = require 'dap'
    local mp1_root = vim.fn.expand '~/dev/uiuc-2026-fall/dlcv-fa26-mps/mp1'
    local mp1_knn = {
      type = 'python',
      request = 'launch',
      name = 'MP1: KNN (100 training images, k=5)',
      program = mp1_root .. '/demo.py',
      cwd = mp1_root,
      pythonPath = python,
      args = { '--classifier', 'knn', '--k', '5', '--num_train', '100' },
      console = 'integratedTerminal',
      justMyCode = false,
    }

    -- Keep this launch target separate from the general Python configurations.
    table.insert(dap.configurations.python, mp1_knn)

    local function debug_mp1_knn()
      dap.run(mp1_knn)
    end

    vim.api.nvim_create_user_command('DebugMP1KNN', debug_mp1_knn, {
      desc = 'Debug the MP1 KNN demo with k=5 and 100 training images',
    })
    vim.keymap.set('n', '<leader>dm', debug_mp1_knn, {
      desc = '[D]ebug [M]P1 KNN demo',
    })
  end,
}
