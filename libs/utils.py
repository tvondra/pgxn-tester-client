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
