return {
  {
    'MeanderingProgrammer/render-markdown.nvim',
    ft = { 'markdown' },
    dependencies = {
      'nvim-treesitter/nvim-treesitter',
      'nvim-mini/mini.icons',
    },
    init = function()
      vim.api.nvim_create_autocmd('FileType', {
        pattern = 'markdown',
        callback = function(event)
          pcall(vim.treesitter.start, event.buf, 'markdown')
        end,
      })
    end,
    opts = {},
    keys = {
      { '<leader>tm', '<cmd>RenderMarkdown toggle<CR>', desc = 'Toggle [M]arkdown rendering' },
      { '<leader>tp', '<cmd>RenderMarkdown preview<CR>', desc = 'Markdown [P]review split' },
    },
  },
}
