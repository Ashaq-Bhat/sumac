PROJECT=SUMAC_Manual

all:
	pdflatex $(PROJECT).tex
	bibtex $(PROJECT)
	pdflatex $(PROJECT).tex
	pdflatex $(PROJECT).tex
	rm -f *.log *.bak *.aux *.bbl *.blg *.idx *.toc *.out *~

rtf:
	latex2rtf $(PROJECT).tex

clean-all:
	rm -f *.dvi *.log *.bak *.aux *.bbl *.blg *.idx *.ps *.eps *.pdf *.toc *.out *~

clean:
	rm -f *.log *.bak *.aux *.bbl *.blg *.idx *.toc *.out *~
