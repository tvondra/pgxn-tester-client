
for i in `seq 1 3`; do

	for pgbin in postgresql-8.2.23  postgresql-8.3.23  postgresql-8.4.21  postgresql-9.0.17  postgresql-9.1.13  postgresql-9.2.8  postgresql-9.3.4  postgresql-9.4beta1; do

		for a in `seq 1 10`; do

	                TMPDIR=./tmp PATH=/home/tomas/work/pgxn-tester/pg/$pgbin/bin:$PATH LANG="C" python run-tests.py --animal testanimal$a --secret testsecret$a > $pgbin.$a.$i.log 2>&1
        	        rm -Rf ./tmp/*

		done
	done

done
