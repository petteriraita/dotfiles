# .latexmkrc 
# Send all temporary LaTeX build files to 'build' inside the same folder


# Always build into ./build
$aux_dir  = 'build';
$out_dir  = 'build';

# Force PDF mode
$pdf_mode = 1;

# Ensure output directory exists
$ENV{'TEXMFOUTPUT'} = 'build';

# CRITICAL FIX: explicitly force synctex into build
$latex = 'pdflatex -synctex=1 -interaction=nonstopmode -output-directory=build %O %S';
