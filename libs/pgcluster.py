#!/usr/bin/python

from datetime import datetime
import subprocess
import StringIO

import os
import shutil
import logging
import tempfile

class PgClusterException(Exception):
	pass

class PgCluster(object):
	'encapsulates initdb and pg_ctl commands, to make the initialization, start and termination of PostgreSQL cluster easier'

	def __init__(self, datadir, logdir):
		'prepare a working cluster'
		self._data = os.path.abspath(datadir)
		self._logdir = os.path.abspath(logdir)

		if os.path.exists(datadir):
			raise PgClusterException("data directory '%(dir)s' already exists" % {'dir' : datadir})

	def _initdb(self):
		'initializes the PostgreSQL cluster, in the selected data directory (may fail for various reasons - e.g. existing directory, ...)'

		logging.info("initializing cluster in '%(data)s' ..." % {'data' : self._data})

		logfile = open('%(dir)s/initdb.log' % {'dir' : self._logdir}, 'w')
		r = subprocess.call(['initdb', '-D', self._data], stdout=logfile, stderr=logfile)

		if r != 0:
			logging.critical("failed to initialize cluster in '%(data)s' (returned %(retval)d)" % {'data' : self._data, 'retval' : r})
			raise PgClusterException("initdb failed")

		logging.info("cluster initialized OK")

	def start(self):
		''
		# initdb of the cluster
		self._initdb()

		logging.info("starting cluster in '%(data)s' ..." % {'data' : self._data})

		logfile = open('%(dir)s/startup.log' % {'dir' : self._logdir}, 'w')
		r = subprocess.call(['pg_ctl', '-D', self._data, '-w', '-l', ('%(dir)s/postgres.log' % {'dir' : self._logdir}), 'start'], stdout=logfile, stderr=logfile)

		if r != 0:
			logging.critical("failed to start cluster in '%(data)s' (returned %(retval)d)" % {'data' : self._data, 'retval' : r})
			raise PgClusterException("pg_ctl start failed")

		logging.info("cluster started OK")

	def _stop(self):

		logging.info("stopping cluster in '%(data)s' ..." % {'data' : self._data})

		logfile = open('%(dir)s/stop.log' % {'dir' : self._logdir}, 'w')
		r = subprocess.call(['pg_ctl', '-D', self._data, 'stop'], stdout=logfile, stderr=logfile)

		if r != 0:
			logging.critical("failed to stop cluster in '%(data)s' (returned %(retval)d)" % {'data' : self._data, 'retval' : r})
			raise PgClusterException("pg_ctl stop failed")

		logging.info("cluster stopped OK")

	def terminate(self, remove=True):
		self._stop()

		if remove:
			logging.info("removing cluster data directory '%(dir)s'" % {'dir' : self._data})
			shutil.rmtree(self._data)

	def info(self):
		(logfile, filename) = tempfile.mkstemp()

		r = subprocess.call(['pg_config'], stdout=logfile, stderr=logfile)
		if r != 0:
			raise PgClusterException("pg_config failed")

		logfile = open(filename, 'r')
		lines = logfile.read().strip().split("\n")
		info = {}

		for l in lines:
			x = l.split('=')
			info.update({x[0].strip() : x[1].strip()})

		return info
