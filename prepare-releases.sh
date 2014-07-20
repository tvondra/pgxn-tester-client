#!/usr/bin/env bash

# directory where the client is placed
SCRIPT="`readlink -f "${BASH_SOURCE[0]}"`"
DIR="`dirname "$SCRIPT"`"

# versions to download / build
VERSIONS="9.4beta1 9.3.4 9.2.8 9.1.13 9.0.17 8.4.21 8.3.23 8.2.23"

# configure options
PGOPTIONS="--enable-cassert --with-perl --with-python --with-tcl --with-libxml --with-libxslt"

PGDIR="$DIR/pg"
BUILDDIR="$DIR/builds"

# start from scratch (remove old builds, compile from scratch)
rm -Rf $PGDIR $BUILDDIR
mkdir -p $PGDIR $BUILDDIR

# number of CPUs (for parallel make)
CPUS=`cat /proc/cpuinfo  | grep 'processor' | wc -l`

for version in $VERSIONS; do

	cd $BUILDDIR

	echo "building PostgreSQL $version"

	wget http://ftp.postgresql.org/pub/source/v$version/postgresql-$version.tar.bz2 > download-$version.log 2>&1

	if [ "$?" != "0" ]; then
		echo "  download failed :-("
		exit 1
	fi

	echo "  downloaded ;-)"

	tar -xjf postgresql-$version.tar.bz2 > unpack-$version.log 2>&1

	if [ "$?" != "0" ]; then
		echo "  extract failed :-("
		exit 1
	fi

	echo "  extracted ;-)"

	cd postgresql-$version

	./configure $PGOPTIONS --prefix=$PGDIR/$version > ../config-$version.log 2>&1

	if [ "$?" != "0" ]; then
		echo "  configure failed :-("
		exit 1
	fi

	echo "  configured ;-)"

	make -j$CPUS install > ../make-$version.log 2>&1

	if [ "$?" != "0" ]; then
		echo "  make failed :-("
		exit 1
	fi

	echo "  make completed ;-)"

	cd ./contrib

	make -j$CPUS install > ../make-contrib-$version.log 2>&1

	if [ "$?" != "0" ]; then
		echo "  make install (contrib) failed :-("
		exit 1
	fi

	echo "  make install (contrib) completed ;-)"

	echo "  build completed OK"

done