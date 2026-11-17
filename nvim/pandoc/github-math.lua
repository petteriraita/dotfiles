-- GitHub permits $`...`$ math; Pandoc parses the backticks as TeX.
-- Normalize parsed math only, leaving Markdown code examples untouched.
function Math(element)
  if element.text:sub(1, 1) == '`' and element.text:sub(-1) == '`' then
    element.text = element.text:sub(2, -2)
  end
  return element
end
