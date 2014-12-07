# TODO

* cleanup of 'tmp' directory
* a script regularly fetching current PostgreSQL versions (currently the versions are hardcoded)
* INSTALL guide
* allow '--force' to test everything
* add instructions on how to operate the client with sufficient security (confine the tests within some sort of container, limit networking ...)
* better dependency / prerequisities handling (currently only PostgreSQL is handled) - this is closely related to the client part
* somehow handling the supported platforms (e.g. Windows-only extension will fail on Linux, ...)
* automatic download / build of new PostgreSQL releases
* allow '--force' in the client, to retest everything (e.g. after fixing a problem on the server configuration, ...)
* getting additional info about the machines (env variables, uname, dmesg, ...)