# PGXN Tester Client

This is the client part of [PGXN Tester][tester], a tool that performs tests on distributions (packages) published at [PostgreSQL Extension Newtwork][pgxn] (aka [PGXN][pgxn]), and submits them to the server.

The ultimate goal of PGXN Tester is providing better tested, more reliable and less fragile distributions to PGXN users. And the first step in this direction is providing regression tests as part of the extensions, running them regularly on range of configurations and reporting the failures with all the details. Running the tests on a range of PostgreSQL versions (those supported by the distribution), various platforms etc. is very tedious, not to mention that many developers don't have easy access some of the platforms. And sometimes things breaks because of changes in the PostgreSQL core itself (e.g. when an API used by an extension is modified).

This is the client part, i.e it downloads, compiles, installs distributions, and executes regression tests (if there are any). And it reports the results back to the server using a simple HTTP/JSON API.

[tester]: http://pgxn-tester.org
[pgxn]: http://pgxn.org


## Security

The one major difference compared to running regression tests of PostgreSQL itself (which is what [pgbuildfarm.org][buildfarm] does) is that while the code commited to PostgreSQL is closely reviewed, running regression tests of distributions essentially means running arbitrary C code downloaded from the Internet.

Although I'm not aware of any "evil" distributions doing nasty things, we should probably assume it's only a matter of time. So you really need to isolate the tests as much as you can - run them with a user with minimum privileges, with no access to important data etc.

The best option is probably running the client in some sort of VM ([LXC][lxc], [kvm][kvm], [vmware][vmware], ...). Although we may provide some ready-made solutions (e.g. using [Vagrant][vagrant] or [Docker][docker]) in the future, at this moment the choice and configuration of the VM is up to you.

[lxc]: https://linuxcontainers.org/
[kvm]: http://www.linux-kvm.org
[vmware]: http://www.vmware.com/
[vagrant]: http://www.vagrantup.com/
[docker]: https://www.docker.com/
[buildfarm]: http://pgbuildfarm.org/


## Issues and Limitations

The system (both client and server part) is imperfect, and there's a lot opportunities for improvement. This sometimes results in false positives or negatives, so take the current results with a grain of salt.

At the moment, only extensions published on PGXN are tested (because we're using PGXN API and [pgxnclient][pgxnclient] to get them). It's possible that sometimes in the future this limitation will be lifted, although it's not a high priority right now.

[pgxnclient]: http://pgxnclient.projects.pgfoundry.org


## Contributing

There are various ways to help this project succeed. You may provide a machine to run the tests once in a while, or you may contribute code - fixing bugs, adding new features etc.

You may also make donations which we can use to cover the costs of running the system, and maybe do things like running tests on and AWS instance with Windows (because this OS is not really common in the community). If you're willing to make a donation, contact me directly.


## Feedback

If you need to discuss something about this site, the best way to do that by posting a message to the [pgxn-users][pgxn-users] group. You may also reach me directly at [tomas@pgaddict.com][mail].

[pgxn-users]: https://groups.google.com/d/forum/pgxn-users
[mail]: mailto:tomas@pgaddict.com


## License

The tool itself is distributed under BSD-style license (see LICENSE).