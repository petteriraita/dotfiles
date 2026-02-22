local ls = require 'luasnip'
local s = ls.snippet
local f = ls.function_node

local i = ls.insert_node
local fmta = require('luasnip.extras.fmt').fmta

local function math()
  return vim.fn['vimtex#syntax#in_mathzone']() == 1
end

ls.add_snippets('tex', {
  s(
    { trig = '([%a])(%d)', regTrig = true, snippetType = 'autosnippet' },
    f(function(_, snip)
      return snip.captures[1] .. '_' .. snip.captures[2]
    end),
    { condition = math }
  ),
})
-- The snippet for the mk math mode
ls.add_snippets('tex', {

  s(
    { trig = 'mk', wordTrig = true, snippetType = 'autosnippet' },

    fmta('\\( <> \\)<>', {

      i(1),

      f(function()
        local pos = vim.api.nvim_win_get_cursor(0)
        local col = pos[2]

        local line = vim.api.nvim_get_current_line()
        local next_char = line:sub(col + 1, col + 1)

        if next_char ~= '' and next_char:match '[%w]' then
          return ' '
        else
          return ''
        end
      end),
    }),

    {
      condition = function()
        return vim.fn['vimtex#syntax#in_mathzone']() == 0
      end,
    }
  ),
})
ls.add_snippets('tex', {
  s(
    { trig = 'ddm', wordTrig = true, snippetType = 'autosnippet' },

    fmta(
      [[
\[
  <>
\]
<>
]],
      {
        i(1),
        i(0),
      }
    ),

    {
      condition = function()
        return vim.fn['vimtex#syntax#in_mathzone']() == 0
      end,
    }
  ),
})
