#!/usr/bin/env python

import argparse
import httplib
import json
import os.path
import re
import shutil
import subprocess
import sys
import time
import uuid
import StringIO
import codecs
import base64
import psutil

from pgxnclient import Spec
from pgxnclient.utils.semver import SemVer

import logging
from datetime import datetime

sys.path.append('libs')

from pgcluster import PgCluster
from utils import sign_request
 
import threading
import time


class TimeoutKiller(threading.Thread):
	
	def __init__(self, timeout=300):
		super(TimeoutKiller, self).__init__()
		self._lock = threading.Lock()
		self._stop = False
		self._timeout = 300
		self._start = time.time()

	def stopped(self):
		'checks state of the _stop flag (with proper locking to get the last value)'

		self._lock.acquire()
		stopped = (self._stop)
		self._lock.release()

		return stopped

	def stop(self):
		'ask the thread to stop (with proper locking to make sure the thread sees the new value)'

		self._lock.acquire()
		self._stop = True
		self._lock.release()

	def run(self):

		# repeat until we get 'stop' request from the parent process, or 
		while (not self.stopped()):

			# sleep for a second (to re-evaluate the stop variable)
			time.sleep(1)

			# we've exceeded the timeout, let's kill 'em all
			if (time.time() - self._start) > self._timeout:

				logging.warning("timeout expired, printing backtraces ...")

				self._print_bt()

				logging.warning("check timed out, killing all remaining postgres processes ...")

				# find all 'postgres' processes and murder them with 'kill -9'
				subprocess.call(['killall', '-9', 'postgres'], stdout=open('/dev/null', 'w'), stderr=open('/dev/null', 'w'))

				# we did what we had to do, so end the thread
				return

	def _print_bt(self):

		# find all postgres processes, run gdb on them
		for p in psutil.process_iter():
			if p.name() == 'postgres':

				print "process pid=",str(p.pid),"cmdline=",str(p.cmdline()),"meminfo",p.memory_info(),"fds=",p.num_fds()

				with open('gdb.log', 'w') as tmp_file:
					subprocess.call(['gdb', '-p', str(p.pid), '-ex', 'bt', '--batch'], stdout=tmp_file, stderr=tmp_file)

				with open('gdb.log', 'r') as tmp_file:
					print "===== back trace ====="
					print tmp_file.read()


def parse_cmdline():
	'''command-line parameter parser'''

	parser = argparse.ArgumentParser(description='PGXN Tester Client')

	parser.add_argument('--data-dir', dest='datadir', default='./data', help='PostgreSQL data directory (default: ./data).')
	parser.add_argument('--log-dir', dest='logdir', default=('logs/' + datetime.now().strftime('%Y%m%d-%H%M%S')), help='log directory (default: ./logs/YYYYmmdd-H24MS)')
	parser.add_argument('--api', dest='api', default='api.pgxn-tester.org', help='API URI (default: api.pgxn-tester.org).')
	parser.add_argument('--debug', dest='debug', action='store_true', default=False, help='debug output (default: false)')

	parser.add_argument('--distribution', dest='distribution', default=None, help='distribution to test')
	parser.add_argument('--version', dest='version', default=None, help='version to test (only with distribution)')

	parser.add_argument('--name', dest='name', required=True, help='machine name')
	parser.add_argument('--secret', dest='secret', required=True, help='secret key')

	return parser.parse_args()


def get_data(host, uri, retries=3, delay=20):
	'''GET requests (with retries), returns JSON object'''

	while (retries > 0):
		retries -= 1

		try:

			conn = httplib.HTTPConnection(host)
			conn.request("GET", uri)
			response = conn.getresponse().read()

			return json.loads(response)

		except Exception as ex:
			logging.warning("attempt to get data from '%(host)s' '%(uri)s' failed: %(msg)s" % {'msg' : str(ex), 'host' : host, 'uri' : uri})
			time.sleep(delay)

		finally:
			conn.close()

	logging.error("attempt to get data from '%(host)s' '%(uri)s' failed: %(msg)s" % {'msg' : str(ex), 'host' : host, 'uri' : uri})


def get_uri_templates(host, prefix):
	'''returns URI templates (JSON dictionary)'''

	templates = get_data(host, prefix)

	for k in templates:
		templates[k] = (prefix+templates[k])

	return templates


def get_distributions(host, templates):
	'''returns list of distributions (packages)'''

	uri = templates['distributions']
	return get_data(host, uri)


def get_distribution_versions(host, templates, dist):
	'''returns list of versions for the given distribution'''

	uri = (templates['distribution'].replace('{name}', dist))
	return get_data(host, uri)


def post_results(host, templates, results, retries=3, delay=20):
	'''posts the result back to the tester server'''

	# post the results (retru in case of failure)
	while (retries > 0):
		retries -= 1
		try:

			conn = httplib.HTTPConnection(host)
			conn.request("POST", templates['results'], json.dumps(results), {"Content-type": "application/json"})
			response = conn.getresponse()

			return (response.status, json.loads(response.read()))

		except Exception as ex:

			logging.warning("attempt to submit result failed: %(msg)s" % {'msg' : str(ex)})
			time.sleep(delay)

	try:
		logging.error("attempt to submit results failed: %(request)s" % {'request' : json.dumps(results, indent=True)})
	except Exception as ex:
		# it might have failed for utf8 issues or whatever, so log the results as text
		logging.error("attempt to submit results failed: %(request)s" % {'request' : results})
		logging.error("can't log the results as JSON: %(msg)s" % {'msg' : str(ex)})

	# send something sensible (-1 does not clash with HTTP codes)
	return (-1, "failed to execute POST request")

def check_prerequisities(pgversion, prereqs):
	'verifies requirements on PostgreSQL version'

	for prereq in prereqs:
		tmp = [v.strip() for v in prereq.split(',')]
		for r in tmp:
			res = re.match('(>|>=|=|==|<=|<)?(\s+)?([0-9]+\.[0-9]+\.[0-9]+)', r)
			if res:
				operator = res.group(1)
				version = SemVer(res.group(3))

				if (operator is None) or (operator == '>='):
					if not (pgversion >= version):
						return False
				elif (operator == '=') or (operator == '=='):
					if not (pgversion == version):
						return False
				elif (operator == '>'):
					if not (pgversion > version):
						return False
				elif (operator == '>='):
					if not (pgversion >= version):
						return False
				elif (operator == '<'):
					if not (pgversion < version):
						return False
				elif (operator == '<='):
					if not (pgversion <= version):
						return False
				else:
					print "unknown operator in prerequisity:",r

			else:
				print "skipping invalid prerequisity :",r

	return True

def run_command(command, log_fname):

	with open(log_fname, 'w') as logfile:
		start_time = time.time()
		r = subprocess.call(command, stdout=logfile, stderr=logfile)
		duration = int(1000 * (time.time() - start_time))

	with codecs.open(log_fname, 'r', encoding='utf-8') as logfile:
		log = logfile.read()

	return (r, log, duration)

def test_release(release, version, state, logdir):
	'''this does all the testing heavy-lifting - calls pgxnclient with install/load/check and records the output'''

	state_opt = ('--%(state)s' % {'state' : state})
	result = {'distribution' : release, 'version' : version, 'install' : 'unknown', 'load' : 'unknown', 'check' : 'unknown', 'check_diff' : '', 'check_log' : '',  'install_log' : '', 'load_log' : '', 'install_duration' : 0, 'check_duration' : 0, 'load_duration' : 0}

	# INITIALIZATION (dropdb/createdb)

	log_fname = '%(dir)s/%(release)s-%(version)s-init.log' % {'dir' : logdir, 'release' : release, 'version' : version}

	with open(log_fname, 'w') as logfile:
		r = subprocess.call(['dropdb', 'pgxntest'], stdout=logfile, stderr=logfile)
		r = subprocess.call(['createdb', 'pgxntest'], stdout=logfile, stderr=logfile)

	# INSTALL

	log_fname = '%(dir)s/%(release)s-%(version)s-install.log' % {'dir' : logdir, 'release' : release, 'version' : version}

	(r, logtext, duration) = run_command(['pgxnclient', 'install', state_opt, '%(release)s=%(version)s' % {'release' : release, 'version' : version}], log_fname)

	result['install_log'] = logtext
	result['install_duration'] = duration

	if r != 0:
		result['install'] = 'error'
		return result
	else:
		result['install'] = 'ok'

	# LOAD

	log_fname = '%(dir)s/%(release)s-%(version)s-load.log' % {'dir' : logdir, 'release' : release, 'version' : version}

	(r, logtext, duration) = run_command(['pgxnclient', 'load', '-d', 'pgxntest', state_opt, '--yes', '%(release)s=%(version)s' % {'release' : release, 'version' : version}], log_fname)

	result['load_log'] = logtext
	result['load_duration'] = duration

	if r != 0:
		result['load'] = 'error'
		return result
	else:
		result['load'] = 'ok'

	# CHECK (installcheck)

	# we need to protect this because of excessively long / hanging checks
	killer = TimeoutKiller()
	killer.start()

	log_fname = '%(dir)s/%(release)s-%(version)s-check.log' % {'dir' : logdir, 'release' : release, 'version' : version}

	(r, logtext, duration) = run_command(['pgxnclient', 'check', state_opt, '%(release)s=%(version)s' % {'release' : release, 'version' : version}], log_fname)

	# we're done, stop the timer
	killer.stop()

	result['check_log'] = logtext
	result['check_duration'] = duration

	# check may fail for various reasons - there may be no 'installcheck' rule in makefile (then it's futile to search for
	# regression.diffs), # or the regression tests may fail (then regression.diffs should be available)
	if r != 0:
		if result['check_log'].find("No rule to make target `installcheck'") >= 0:
			result['check'] = 'missing'
		elif result['check_log'].find("Nothing to be done for `installcheck'") >= 0:
			result['check'] = 'missing'
		else:
			# find the diff file
			res = re.search('"([^"]*.diffs)"', result['check_log'])
			if res:
				with codecs.open(res.group(1), 'r', encoding='utf-8') as diff:
					result['check_diff'] = diff.read()

			result['check'] = 'error'
			return result
	else:
		# meh, make returns 0 in this case, so we need to handle it specifically
		if result['check_log'].find("Nothing to be done for `installcheck'") >= 0:
			result['check'] = 'missing'
		else:
			result['check'] = 'ok'

	return result

def parse_api_uri(uri):

	if '/' in uri:
		tmp = uri.split('/')
		return (tmp[0], '/' . join(tmp[1:]))
	else:
		return (uri, '')

def create_log_directory(logdir):

	logging.info("log directory '%(dir)s'" % {'dir' : logdir})

	if not os.path.exists(logdir):
		# ok, the path does not exist, so just create the directory
		os.makedirs(logdir)
	elif not os.path.isdir(logdir):
		logging.error("path '%(dir)s' exists, but is not directory" % {'dir' : logdir})
		sys.exit(1)
	else:
		logging.warning("log directory '%(dir)s' already exists" % {'dir' : logdir})

def init_logging(debug=False):

	# by default, we're logging just INFO and above
	level=logging.INFO

	if debug:
		level=logging.DEBUG

	logging.basicConfig(level=level, format='%(asctime)-15s %(levelname)s %(message)s')

if __name__ == '__main__':

	cluster = None

	# parse arguments first
	args = parse_cmdline()

	# initialize the logging system
	init_logging(args.debug)

	# create log directory, if not exists
	create_log_directory(args.logdir)

	# split the API URI into host/prefix
	(api_host, api_prefix) = parse_api_uri(args.api)

	logging.info("using API host='%(host)s' prefix='%(prefix)s'" % {'host' : api_host, 'prefix' : api_prefix})

	# do this in try/except block, so that we can stop the cluster in case of failure
	try:

		# now get URI templates (this should query actual packages)
		templates = get_uri_templates(api_host, api_prefix)

		# get list of all distributions
		distributions = get_distributions(api_host, templates)

		logging.info("received list of %(len)d distributions to test" % {'len' : len(distributions)})

		# loop through the distributions
		for dist in distributions:

			# if distribution supplied (and does not match, skip)
			if args.distribution is not None and args.distribution != dist['name']:
				continue

			# get versions for the distribution
			info = get_distribution_versions(api_host, templates, dist['name'])

			# ignore users with no releases
			if (not info) or (not info['versions']):
				log.warning("no versions for distribution '%(name)s' found" % {'name' : dist['name']})
				continue

			logging.info("received %(len)d versions for '%(name)s' distribution" % {'len' : len(info['versions']), 'name' : dist['name']})

			# loop through versions of this distribution
			for version in info['versions']:

				# if version supplied (and does not match, skip)
				if (args.distribution is not None) and (args.version is not None) and (args.version != version['version']):
					continue

				logging.info("testing '%(name)s-%(version)s' (%(status)s)" % {'name' : dist['name'], 'version' : version['version'], 'status' : version['status']})

				# get package prerequisities (extracted from META.json by the server)
				prereqs = version['prereqs']

				cluster = None

				# only create the wrapper, so that we can call pg_config (to get the version - don't do inidb/start)
				cluster = PgCluster(datadir=args.datadir, logdir=args.logdir)

				# output from pg_config (as a dictionary)
				pginfo = cluster.info()

				# get the version number only
				# FIXME this default is wrong
				pgversion = SemVer('9.4.0')
				try:
					pgversion = SemVer((pginfo['VERSION'].split(' '))[1])
				except:
					pass


				# run the build only if the prerequisities are OK
				if check_prerequisities(pgversion, prereqs):

					try:

						# start the cluster and do the testing
						cluster.start()

						logging.info("PostgreSQL cluster started, version = %(version)s" % {'version' : pgversion})

						# run the actual test
						result = test_release(dist['name'], version['version'], version['status'], logdir=args.logdir)

						# additional info, and a random UUID for the result (we're generating it here as a protection against simple replay attacks)
						result.update({'uuid' : str(uuid.uuid4()), 'machine' : args.name, 'config' : json.dumps(pginfo), 'env' : json.dumps({})})

						# there has to be a better way ... but well, this seems to work for now
						result['install_log'] = base64.b64encode(result['install_log'].encode('utf-8'))
						result['load_log'] = base64.b64encode(result['load_log'].encode('utf-8'))
						result['check_log'] = base64.b64encode(result['check_log'].encode('utf-8'))
						result['check_diff'] = base64.b64encode(result['check_diff'].encode('utf-8'))

						# sign the request with the shared secret
						result = sign_request(result, args.secret)

						# do the POST request (if OK, status is 200)
						(status, reason) = post_results(api_host, templates, result)

						if (status == 200):
							logging.info("POST OK : UUID='%(uuid)s' install=%(install)s load=%(load)s check=%(check)s" % {'uuid' : reason['uuid'], 'install' : result['install'], 'load' : result['load'], 'check' : result['check']})
						else:
							logging.error(reason)
							logging.error("POST for %(dist)s-%(version)s failed (status = %(status)d)" % {'dist' : dist['name'], 'version' : version['version'], 'status' : status})

					except Exception as ex:

						logging.info("testing failed: %(msg)s" % {'msg' : str(ex)})
						logging.exception(ex)

					finally:

						# stop the PostgreSQL cluster and remove the data directory
						if cluster:
							logging.info("removing DATA directory")
							cluster.terminate()

				else:

					logging.info("%(dist)s-%(version)s skipped - unmet PostgreSQL version (current %(pgversion)s, needs %(prereqs)s)" % {'dist' : dist['name'], 'version' : version['version'], 'prereqs' : prereqs, 'pgversion' : pgversion})


	except Exception as ex:
		logging.info("testing failed: %(msg)s" % {'msg' : str(ex)})
		logging.exception(ex)
