import hashlib

def sign_request(data, secret):
	'simple JSON signing with a shared secret'

	keys = data.keys()
	digest = hashlib.sha256()
	digest.update(secret)

	keys = sorted(data.keys())

	for k in keys:
		digest.update(k)
		digest.update(':')
		digest.update(str(data[k]))
		digest.update(';')

	data.update({'signature' : digest.hexdigest()})

	return data

def verify_signature(data, secret, signature):
	'repeats the JSON signing and compares the signatures'

	return (sign_request(data, secret) == signature)


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
