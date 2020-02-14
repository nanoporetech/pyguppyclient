CONFIG      ?= dna_r9.4.1_450bps_fast
CORECPPDIR  ?= ../ont_core_cpp
TESTDATAURL ?= https://nanoporetech.box.com/shared/static/hpeyme4posfzmc0hcxh0nl5tiuzjfbzf.gz
TESTDATADIR ?= tests/reads
DATADIR     ?= $(TESTDATADIR)/testdata/

tests/reads:
	mkdir -p $(TESTDATADIR)
	wget -q --show-progress --max-redirect=9 -O $(TESTDATADIR)/reads.tar.gz $(TESTDATAURL)
	tar xf $(TESTDATADIR)/reads.tar.gz -C $(TESTDATADIR)
	rm $(TESTDATADIR)/reads.tar.gz

clean:
	rm -rf *.egg-info *~ *.log* build dist *.fasta *.fastq *lprof *.fa *.fq

build:
	flatc -o pyguppyclient --python $(CORECPPDIR)/ont_core/ipc_tools/guppy_ipc_schema.fbs
	sed -i 's/from guppy_ipc/from pyguppyclient.guppy_ipc/' pyguppyclient/guppy_ipc/*.py

test: tests/reads
	nosetests -v --with-doctest --with-coverage --cover-package pyguppyclient
	python3 examples/pyguppyclient -t 5 ${CONFIG} ${DATADIR}/multi > /dev/null
	python3 examples/pyguppyclient -t 5 ${CONFIG} ${DATADIR}/single > /dev/null

example: tests/reads
	python3 examples/pyguppyclient -t 5 ${CONFIG} ${DATADIR}/multi > pyguppyclient.fastq
