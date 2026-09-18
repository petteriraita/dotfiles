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
    opts = {
      -- Keep the editing buffer stable. Properly typeset math is available in
      -- the synchronized browser preview below.
      latex = { enabled = false },
    },
    keys = {
      { '<leader>tm', '<cmd>RenderMarkdown toggle<CR>', desc = 'Toggle [M]arkdown rendering' },
    },
  },
  {
    'iamcco/markdown-preview.nvim',
    -- The local GitHub-math compatibility patch in pages/katex.js is built
    -- into the preview. Do not overwrite it during a general plugin update.
    pin = true,
    cmd = { 'MarkdownPreviewToggle', 'MarkdownPreview', 'MarkdownPreviewStop' },
    ft = { 'markdown' },
    build = 'cd app && npm install',
    init = function()
      vim.g.mkdp_filetypes = { 'markdown' }
      vim.g.mkdp_theme = 'dark'
      vim.g.mkdp_auto_close = 1
      vim.g.mkdp_combine_preview = 1
    end,
    keys = {
      { '<leader>tp', '<cmd>MarkdownPreviewToggle<CR>', desc = 'Toggle Markdown browser [P]review' },
    },
  },
}
