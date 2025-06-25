" ================================================
" Clipboard Integration Settings
" ================================================
" lskfjlakjf " 
" Enable system CLIPBOARD integration
set clipboard=unnamedplus

" ================================================
" General Settings
" ================================================


augroup YankDeleteChangeToClipboard
  autocmd!
  autocmd TextYankPost * if v:event.operator =~# '[ydc]' && v:event.regname =~# '[a-z]' | call setreg('+', getreg(v:event.regname)) | endif
augroup END


" Display line numbers
set number
set relativenumber


" Disable search highlighting
set nohlsearch

" setting up the spaces well
set autoindent
set smartindent
set cindent
set cinoptions+=j1  " Keep opening braces { on the same line

