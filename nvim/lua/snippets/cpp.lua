local ls = require 'luasnip'
local rep = require('luasnip.extras').rep

local function mirrored(trigger, before, middle, after)
  return ls.snippet(trigger, {
    ls.text_node(before),
    rep(1),
    ls.text_node(middle),
    ls.insert_node(1),
    ls.text_node(after),
  })
end

return {
  mirrored('clv', 'std::cout << "', ': " << ', ' << std::endl;'),
  mirrored('clvn', 'std::cout << "', ':\\n" << ', ' << std::endl;'),
  mirrored('clvt', 'std::cout << "type(', '): " << typeid(', ').name() << std::endl;'),
}
