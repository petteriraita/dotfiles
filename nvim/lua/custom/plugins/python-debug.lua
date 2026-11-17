return {
  'mfussenegger/nvim-dap-python',
  ft = 'python',
  dependencies = { 'mfussenegger/nvim-dap' },
  config = function()
    local python = vim.fn.expand '~/miniconda3/envs/py310/bin/python'
    local mp1_root = vim.fn.expand '~/dev/school/uiuc/2026-fall/ECE_494_Deep_Learning_for_Computer_Vision/mp1'
    local mp2_root = vim.fn.expand '~/dev/school/uiuc/2026-fall/ECE_494_Deep_Learning_for_Computer_Vision/mp2'
    local mp3_root = vim.fn.expand '~/dev/school/uiuc/2026-fall/ECE_494_Deep_Learning_for_Computer_Vision/mp3'
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
    local mp1_logistic_small = {
      type = 'python',
      request = 'launch',
      name = 'MP1: Logistic (wt=1e-3, 15 training images)',
      program = mp1_root .. '/demo.py',
      cwd = mp1_root,
      pythonPath = python,
      args = { '--classifier', 'logistic', '--lr', '1e-1', '--wt', '1e-3', '--num_train', '15', '--out_dir', 'runs/logistic' },
      console = 'integratedTerminal',
      justMyCode = false,
    }
    local mp1_linear_small = {
      type = 'python',
      request = 'launch',
      name = 'MP1: Linear (wt=1e-3, 10 training images)',
      program = mp1_root .. '/demo.py',
      cwd = mp1_root,
      pythonPath = python,
      args = { '--classifier', 'linear', '--wt', '1e-3', '--num_train', '10', '--out_dir', 'runs/linear' },
      console = 'integratedTerminal',
      justMyCode = false,
    }
    local cv_mp2_relu_forward = {
      type = 'python',
      request = 'launch',
      name = 'CV MP2: CURRENT',
      module = 'unittest',
      cwd = mp2_root,
      pythonPath = python,
      args = {
        'test_layers.TestLayersAndLosses.test_layer_maxpool_forward',
        -- 'test_layers.TestLayersAndLosses.test_loss_softmax_with_logits_forward',
        -- 'test_layers.TestLayersAndLosses.test_loss_softmax_with_logits_grad_x',
        -- 'test_layers.TestLayersAndLosses.test_layer_relu_forward',
        -- 'test_layers.TestLayersAndLosses.test_layer_relu_grad_input',
        '-v',
      },
      console = 'integratedTerminal',
      justMyCode = false,
    }
    local cv_mp2_linear_demo = {
      type = 'python',
      request = 'launch',
      name = 'CV MP2: Linear demo (10 epochs)',
      program = mp2_root .. '/demo.py',
      cwd = mp2_root,
      pythonPath = python,
      args = { '--classifier', 'linear', '--lr', '1e-2', '--gamma', '0.9', '--epochs', '10' },
      console = 'integratedTerminal',
      justMyCode = false,
    }
    local cv_mp3_flower_fake = {
      type = 'python',
      request = 'launch',
      name = 'CV MP3: Flower fake local run',
      program = mp3_root .. '/demo_flower.py',
      cwd = mp3_root,
      pythonPath = python,
      args = { '--exp_name', 'vit_prompt', '--debug_fake_data', '--output_dir', 'runs_flower/debug_fake' },
      console = 'integratedTerminal',
      justMyCode = false,
    }
    -- python -m unittest test_layers.TestLayersAndLosses.test_loss_softmax_with_logits_forward test_layers.TestLayersAndLosses.test_loss_softmax_with_logits_grad_x -v
    require('custom.python_debug_reload').apply(python, {
      mp1_knn,
      mp1_linear_small,
      mp1_logistic_small,
      cv_mp2_relu_forward,
      cv_mp2_linear_demo,
      cv_mp3_flower_fake,
      {
        type = 'python',
        request = 'launch',
        name = 'CV MP3: PixMo fake local run',
        program = mp3_root .. '/demo_pixmo.py',
        cwd = mp3_root,
        pythonPath = python,
        args = { '--exp_name', 'pixmo_demo', '--debug_fake_data', '--output_dir', 'runs_pixmo/debug_fake' },
        console = 'integratedTerminal',
        justMyCode = false,
      },
    })
  end,
}
