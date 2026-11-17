local M = {}

local initialized = false
local owned = {}

function M.reload(silent)
  local path = vim.fn.stdpath('config') .. '/lua/custom/plugins/python-debug.lua'
  local chunk, err = loadfile(path)
  if not chunk then
    vim.notify('Python debug config: ' .. err, vim.log.levels.ERROR)
    return
  end

  local ok, spec = pcall(chunk)
  if not ok or type(spec) ~= 'table' or type(spec.config) ~= 'function' then
    vim.notify('Python debug config: ' .. tostring(spec), vim.log.levels.ERROR)
    return
  end

  if not initialized then
    require('lazy').load({ plugins = { 'nvim-dap-python' } })
  end

  local applied, apply_err = pcall(spec.config)
  if applied and not silent then
    vim.notify('Python debug targets reloaded')
  elseif not applied then
    vim.notify('Python debug config: ' .. tostring(apply_err), vim.log.levels.ERROR)
  end
end

function M.apply(python, targets)
  local dap = require('dap')
  if not M.provider_installed then
    local original = dap.providers.configs['dap.global']
    dap.providers.configs['dap.global'] = function(bufnr)
      if vim.bo[bufnr].filetype == 'python' then
        M.reload(true)
      end
      return original(bufnr)
    end
    M.provider_installed = true
  end
  -- Reconfigure the adapter, but add dap-python's general targets only once.
  require('dap-python').setup(python, { include_configs = not initialized })
  initialized = true

  local configs = require('dap').configurations.python
  for i = #configs, 1, -1 do
    if owned[configs[i]] then
      table.remove(configs, i)
    end
  end

  owned = {}
  for _, target in ipairs(targets) do
    table.insert(configs, target)
    owned[target] = true
  end
end

function M.enable()
  local path = vim.fn.stdpath('config') .. '/lua/custom/plugins/python-debug.lua'
  local group = vim.api.nvim_create_augroup('PythonDebugConfigReload', { clear = true })

  pcall(vim.api.nvim_del_user_command, 'DapReloadPythonConfigs')
  vim.api.nvim_create_user_command('DapReloadPythonConfigs', M.reload, {
    desc = 'Reload the configured Python DAP launch targets',
  })

  vim.api.nvim_create_autocmd('BufWritePost', {
    group = group,
    callback = function(event)
      local saved = vim.api.nvim_buf_get_name(event.buf)
      if vim.uv.fs_realpath(saved) ~= vim.uv.fs_realpath(path) then
        return
      end

      M.reload()
    end,
  })
end

return M
