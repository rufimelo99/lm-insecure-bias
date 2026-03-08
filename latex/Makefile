TEX = artifact_abstract
LATEX = pdflatex

all: $(TEX).pdf

$(TEX).pdf: $(TEX).tex
	$(LATEX) $(TEX).tex
	$(LATEX) $(TEX).tex

clean:
	rm -f $(TEX).aux $(TEX).log $(TEX).out $(TEX).toc $(TEX).bbl $(TEX).blg

distclean: clean
	rm -f $(TEX).pdf
