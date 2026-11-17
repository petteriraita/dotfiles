return {
  {
    'folke/flash.nvim',
    event = 'VeryLazy',
    opts = {
      modes = {
        char = {
          multi_line = true,
        },
      },
    },
  },
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
      -- Keep a manually opened preview alive when changing buffers.
      vim.g.mkdp_auto_close = 0
      vim.g.mkdp_combine_preview = 1

      -- markdown-preview.nvim's localhost server is an RPC child of Neovim,
      -- so it necessarily ends with Neovim.  This command creates an offline
      -- HTML snapshot instead; its browser tab remains usable after Neovim
      -- exits.  Re-run it to refresh the snapshot after making edits.
      vim.api.nvim_create_user_command('MarkdownPersistentPreview', function()
        local source_path = vim.api.nvim_buf_get_name(0)
        if source_path == '' then
          vim.notify('Save the Markdown file before creating a persistent preview.', vim.log.levels.WARN)
          return
        end

        local output_dir = vim.fs.joinpath(vim.fn.stdpath('cache'), 'markdown-previews')
        local server_port = 8765
        vim.fn.mkdir(output_dir, 'p')
        local output_path = vim.fs.joinpath(output_dir, vim.fn.sha256(source_path) .. '.html')
        local markdown = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), '\n')
        local title = vim.fn.fnamemodify(source_path, ':t')

        vim.system({
          'pandoc', '--from=markdown', '--to=html5', '--standalone', '--embed-resources', '--mathml',
          '--lua-filter', vim.fs.joinpath(vim.fn.stdpath('config'), 'pandoc', 'github-math.lua'),
          '--metadata', 'title=' .. title, '--output', output_path,
        }, {
          cwd = vim.fn.fnamemodify(source_path, ':h'),
          stdin = markdown,
          text = true,
        }, function(result)
          vim.schedule(function()
            if result.code ~= 0 then
              vim.notify('Pandoc could not create the preview: ' .. result.stderr, vim.log.levels.ERROR)
              return
            end
            -- This detached server outlives Neovim.  Using its HTTP URL also
            -- lets xdg-open use the normal browser handler instead of the
            -- text/html handler (which is intentionally associated with nvim).
            vim.fn.jobstart({
              'python3', '-m', 'http.server', tostring(server_port),
              '--bind', '127.0.0.1', '--directory', output_dir,
            }, { detach = true })
            vim.defer_fn(function()
              vim.fn.jobstart({
                'xdg-open', ('http://127.0.0.1:%d/%s.html'):format(server_port, vim.fn.sha256(source_path)),
              }, { detach = true })
            end, 100)
          end)
        end)
      end, { desc = 'Create a persistent Markdown HTML preview' })
    end,
    keys = {
      { '<leader>tp', '<cmd>MarkdownPersistentPreview<CR>', desc = 'Open [P]ersistent Markdown preview' },
      { '<leader>tP', '<cmd>MarkdownPreviewToggle<CR>', desc = 'Toggle [live] Markdown preview' },
    },
  },
}
