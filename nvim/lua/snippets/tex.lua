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
    { trig = 'dm', wordTrig = true, snippetType = 'autosnippet' },

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

--add the begin snippet block
local rep = require('luasnip.extras').rep
ls.add_snippets('tex', {

  s(
    { trig = 'beg', snippetType = 'autosnippet', line_begin = true },

    fmta(
      [[
\begin{<>}
  <>
\end{<>}
]],
      {
        i(1), -- environment name
        i(0), -- body
        rep(1), -- repeat env name
      }
    )
  ),
})

--GPT code for the fraction snippet
--
local function split_last_paren(str)
  local depth = 0
  for idx = #str, 1, -1 do
    local ch = str:sub(idx, idx)
    if ch == ')' then
      depth = depth + 1
    elseif ch == '(' then
      depth = depth - 1
      if depth == 0 then
        return str:sub(1, idx - 1), str:sub(idx + 1, #str - 1)
      end
    end
  end
  return nil, nil
end

ls.add_snippets('tex', {
  -- // -> \frac{}{}
  s(
    { trig = '//', snippetType = 'autosnippet', priority = 800 },
    fmta('\\frac{<>}{<>}', {
      i(1),
      i(2),
    }),
    { condition = math }
  ),

  -- 3/ , a_2/ , \pi/ , 4\pi^2/  -> \frac{...}{}
  s(
    { trig = '([%w\\{}_^]+)/', regTrig = true, snippetType = 'autosnippet', priority = 900 },
    fmta('\\frac{<>}{<>}', {
      f(function(_, snip)
        return snip.captures[1]
      end),
      i(1),
    }),
    { condition = math }
  ),

  -- (1+2+3)/ and (1+(2+3))/ and (1+(2+3)/)
  s(
    { trig = '^(.*%))/', regTrig = true, snippetType = 'autosnippet', priority = 1000 },
    fmta('<>\\frac{<>}{<>}', {
      f(function(_, snip)
        local prefix, _ = split_last_paren(snip.captures[1])
        return prefix or ''
      end),
      f(function(_, snip)
        local _, inner = split_last_paren(snip.captures[1])
        return inner or snip.captures[1]
      end),
      i(1),
    }),
    { condition = math }
  ),
})
