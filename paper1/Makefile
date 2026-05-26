PAPER := main
LATEX := pdflatex -interaction=nonstopmode -halt-on-error
BIBTEX := bibtex

.PHONY: pdf clean view distclean

pdf: $(PAPER).pdf

$(PAPER).pdf: $(PAPER).tex appendix.tex refs.bib $(wildcard figures/*.pdf)
	$(LATEX) $(PAPER).tex
	-$(BIBTEX) $(PAPER)
	$(LATEX) $(PAPER).tex
	$(LATEX) $(PAPER).tex

clean:
	rm -f $(PAPER).aux $(PAPER).log $(PAPER).out $(PAPER).bbl $(PAPER).blg \
	      $(PAPER).toc $(PAPER).fls $(PAPER).fdb_latexmk \
	      appendix.aux

distclean: clean
	rm -f $(PAPER).pdf

view: pdf
	@xdg-open $(PAPER).pdf 2>/dev/null || open $(PAPER).pdf
