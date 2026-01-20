" ================================================
" Clipboard Integration Settings
" ================================================
" If you need to test if this rc file is hit, then uncomment this below
"echom "VIMRC HIT"

" autocmd VimEnter * echoerr "VIMRC DEFINITELY LOADED"

" Enable system CLIPBOARD integration
set clipboard=unnamedplus

" ================================================
" General Settings
" ================================================


" Explicit cursor shapes (works in tmux + xterm-like terminals)
if &term =~ "xterm\\|tmux"
  let &t_SI = "\e[5 q"   " insert mode: beam
  let &t_EI = "\e[1 q"   " normal mode: block
endif


augroup YankDeleteChangeToClipboard
  autocmd!
  autocmd TextYankPost * if v:event.operator =~# '[ydc]' && v:event.regname =~# '[a-z]' | call setreg('+', getreg(v:event.regname)) | endif
augroup END


" Display line numbers
set number
set relativenumber


" Disable search highlighting
set nohlsearch
" change the command line introducer
nnoremap ; :
vnoremap ; :

" setting up the spaces well
set autoindent
" set the indentation to be specific for each language
augroup CLangs
  autocmd!
  autocmd FileType c,cpp,java setlocal cindent
  autocmd FileType c,cpp,java setlocal cinoptions+=j1
augroup END

augroup PythonIndent
  autocmd!
  " ensure Python uses its own indenter, not cindent
  autocmd FileType python setlocal nocindent nosmartindent
  " canonical Python spaces
  autocmd FileType python setlocal expandtab shiftwidth=4 softtabstop=4 tabstop=4
augroup END


