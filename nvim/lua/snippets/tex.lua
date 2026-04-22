local ls = require 'luasnip'
local s = ls.snippet
local f = ls.function_node
local t = ls.text_node
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
    { trig = 'bgn', snippetType = 'autosnippet', line_begin = true },

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

-- the ttt text
ls.add_snippets('tex', {
  s(
    { trig = 'tt', wordTrig = true, snippetType = 'autosnippet' },
    fmta('\\texttt{ <> }', {
      i(1),
    }),
    { condition = math }
  ),
})
-- the text
ls.add_snippets('tex', {
  s(
    { trig = 'tx', wordTrig = true, snippetType = 'autosnippet' },
    fmta('\\text{ <> }', {
      i(1),
    }),
    { condition = math }
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

--the greek letters automatching
ls.add_snippets('tex', {
  -- lowercase
  s({ trig = ';a', snippetType = 'autosnippet' }, { t '\\alpha' }),
  s({ trig = ';b', snippetType = 'autosnippet' }, { t '\\beta' }),
  s({ trig = ';g', snippetType = 'autosnippet' }, { t '\\gamma' }),
  s({ trig = ';d', snippetType = 'autosnippet' }, { t '\\delta' }),
  s({ trig = ';e', snippetType = 'autosnippet' }, { t '\\epsilon' }),
  s({ trig = ';z', snippetType = 'autosnippet' }, { t '\\zeta' }),
  s({ trig = ';h', snippetType = 'autosnippet' }, { t '\\eta' }),
  s({ trig = ';t', snippetType = 'autosnippet' }, { t '\\theta' }),
  s({ trig = ';i', snippetType = 'autosnippet' }, { t '\\iota' }),
  s({ trig = ';k', snippetType = 'autosnippet' }, { t '\\kappa' }),
  s({ trig = ';l', snippetType = 'autosnippet' }, { t '\\lambda' }),
  s({ trig = ';m', snippetType = 'autosnippet' }, { t '\\mu' }),
  s({ trig = ';n', snippetType = 'autosnippet' }, { t '\\nu' }),
  s({ trig = ';x', snippetType = 'autosnippet' }, { t '\\xi' }),
  s({ trig = ';o', snippetType = 'autosnippet' }, { t '\\omicron' }),
  s({ trig = ';p', snippetType = 'autosnippet' }, { t '\\pi' }),
  s({ trig = ';r', snippetType = 'autosnippet' }, { t '\\rho' }),
  s({ trig = ';s', snippetType = 'autosnippet' }, { t '\\sigma' }),
  s({ trig = ';u', snippetType = 'autosnippet' }, { t '\\tau' }),
  s({ trig = ';y', snippetType = 'autosnippet' }, { t '\\upsilon' }),
  s({ trig = ';f', snippetType = 'autosnippet' }, { t '\\phi' }),
  s({ trig = ';c', snippetType = 'autosnippet' }, { t '\\chi' }),
  s({ trig = ';ps', snippetType = 'autosnippet' }, { t '\\psi' }),
  s({ trig = ';w', snippetType = 'autosnippet' }, { t '\\omega' }),

  -- uppercase
  s({ trig = ';A', snippetType = 'autosnippet' }, { t '\\Alpha' }),
  s({ trig = ';B', snippetType = 'autosnippet' }, { t '\\Beta' }),
  s({ trig = ';G', snippetType = 'autosnippet' }, { t '\\Gamma' }),
  s({ trig = ';D', snippetType = 'autosnippet' }, { t '\\Delta' }),
  s({ trig = ';E', snippetType = 'autosnippet' }, { t '\\Epsilon' }),
  s({ trig = ';Z', snippetType = 'autosnippet' }, { t '\\Zeta' }),
  s({ trig = ';H', snippetType = 'autosnippet' }, { t '\\Eta' }),
  s({ trig = ';T', snippetType = 'autosnippet' }, { t '\\Theta' }),
  s({ trig = ';I', snippetType = 'autosnippet' }, { t '\\Iota' }),
  s({ trig = ';K', snippetType = 'autosnippet' }, { t '\\Kappa' }),
  s({ trig = ';L', snippetType = 'autosnippet' }, { t '\\Lambda' }),
  s({ trig = ';M', snippetType = 'autosnippet' }, { t '\\Mu' }),
  s({ trig = ';N', snippetType = 'autosnippet' }, { t '\\Nu' }),
  s({ trig = ';X', snippetType = 'autosnippet' }, { t '\\Xi' }),
  s({ trig = ';O', snippetType = 'autosnippet' }, { t '\\Omicron' }),
  s({ trig = ';P', snippetType = 'autosnippet' }, { t '\\Pi' }),
  s({ trig = ';R', snippetType = 'autosnippet' }, { t '\\Rho' }),
  s({ trig = ';S', snippetType = 'autosnippet' }, { t '\\Sigma' }),
  s({ trig = ';U', snippetType = 'autosnippet' }, { t '\\Tau' }),
  s({ trig = ';Y', snippetType = 'autosnippet' }, { t '\\Upsilon' }),
  s({ trig = ';F', snippetType = 'autosnippet' }, { t '\\Phi' }),
  s({ trig = ';C', snippetType = 'autosnippet' }, { t '\\Chi' }),
  s({ trig = ';PS', snippetType = 'autosnippet' }, { t '\\Psi' }),
  s({ trig = ';W', snippetType = 'autosnippet' }, { t '\\Omega' }),
}, { condition = math })
