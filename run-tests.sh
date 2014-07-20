#!/usr/bin/env bash

# directory where the client is placed
SCRIPT="`readlink -f "${BASH_SOURCE[0]}"`"
DIR="`dirname "$SCRIPT"`"

# which PostgreSQL versions to test?
VERSIONS="9.4beta1 9.3.4 9.2.8 9.1.13 9.0.17 8.4.21 8.3.23 8.2.23"

# machine identification
NAME="testmachine"
SECRET="secretkey"

# influences things like message language etc.
LANG="C"

# important directories
PGDIR="$DIR/pg"
TMPDIR="$DIR/tmp"

# by default we'll return 0 (everything OK)
retval=0

# loop through the PostgreSQL versions
for version in $VERSIONS; do

	if [ ! -d "$PGDIR/$version" ]; then

		echo "ERROR: PostgreSQL '$version' not available at '$PGDIR/$version' (not built?)"
		retval=1

	else

		echo "running tests on PostgreSQL $version"

		# make the 'tmp' directory
		mkdir -p $TMPDIR

		# run the tests
		TMPDIR=$TMPDIR PATH="$PGDIR/$version/bin:$PATH" LANG=$LANG ./run-tests.py --name "$NAME" --secret "$SECRET" >> $DIR/logs/test-$version.log 2>&1

		if [ "$?" != "0" ]; then
			echo "ERROR: running tests on PostgreSQL $version failed (retval=$?)"
			retval=1
		fi

		# remove the 'tmp' directory (files left over by pgxnclient)
		rm -Rf $TMPDIR

	fi

done

# 0 - everything OK, 1 - missing PostgreSQL build or error when running the tests
exit $retval
