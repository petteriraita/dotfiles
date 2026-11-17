-- :S*pattern*replacement*flags uses Vim search patterns and literal replacement text.
local function substitute(opts)
  local input = opts.args
  if input:sub(1, 1) ~= '*' then
    error('Use :S*pattern*literal replacement*flags')
  end

  local separator
  local escaped = false
  for i = 2, #input do
    local char = input:sub(i, i)
    if char == '*' and not escaped then
      separator = i
      break
    end
    if char == '\\' then
      escaped = not escaped
    else
      escaped = false
    end
  end
  if not separator then
    error('Missing separator after search pattern')
  end

  local pattern = input:sub(2, separator - 1)
  local tail = input:sub(separator + 1)
  local ending = tail:find('*', 1, true)
  local replacement = ending and tail:sub(1, ending - 1) or tail
  local flags = ending and tail:sub(ending + 1) or ''
  if not flags:match('^[gicInep#l]*$') then
    error('Invalid substitute flags: ' .. flags)
  end
  local range = opts.line1 .. ',' .. opts.line2
  vim.cmd(range .. 's*' .. pattern .. '*' .. vim.fn.escape(replacement, [[\&~]]) .. '*' .. flags)
end

vim.api.nvim_create_user_command('S', substitute, { nargs = 1, range = true, desc = 'Substitute with literal replacement' })
