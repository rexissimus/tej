"""Entry point for the tej utility.
"""

from __future__ import unicode_literals

import argparse
import codecs
import locale
import logging
import sys

from tej import __version__ as tej_version
from tej.submission import DEFAULT_TEJ_DIR, Error, JobNotFound, RemoteQueue


logger = logging.getLogger('tej')


def setup_logging(verbosity):
    levels = [logging.CRITICAL, logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(verbosity, 3)]

    fmt = "%(asctime)s %(levelname)s: %(message)s"
    formatter = logging.Formatter(fmt)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.getLogger().addHandler(handler)
    logger.setLevel(level)

    # Prints output from server to stderr
    server = logging.getLogger('tej.server')
    server.propagate = False
    raw_console = logging.StreamHandler(sys.stderr)
    raw_console.setFormatter(logging.Formatter('%(message)s'))
    server.addHandler(raw_console)


def _setup(args):
    RemoteQueue(args.destination, args.queue).setup(args.make_link, args.force,
                                                    args.only_links)


def _submit(args):
    job_id = RemoteQueue(args.destination, args.queue).submit(
                         args.id, args.directory, args.script)
    print(job_id)


def _status(args):
    if args.id is None:
        logger.critical("Missing job identifier")
        sys.exit(1)
    try:
        queue = RemoteQueue(args.destination, args.queue)
        status, directory, arg = queue.status(args.id)
        if status == RemoteQueue.JOB_DONE:
            sys.stdout.write("finished")
        elif status == RemoteQueue.JOB_RUNNING:
            sys.stdout.write("running")
        else:
            raise RuntimeError("Got unknown job status %r" % status)
        if arg is not None:
            sys.stdout.write(' %s' % arg)
        sys.stdout.write('\n')
    except JobNotFound:
        print("not found")


def _download(args):
    RemoteQueue(args.destination, args.queue).download(args.id, args.files,
                                                       directory='.')


def _kill(args):
    RemoteQueue(args.destination, args.queue).kill(args.id)


def _delete(args):
    RemoteQueue(args.destination, args.queue).delete(args.id)


def _list(args):
    for job_id, info in RemoteQueue(args.destination, args.queue).list():
        sys.stdout.write("%s %s\n" % (job_id, info['status']))


def main():
    """Entry point when called on the command-line.
    """
    # Locale
    locale.setlocale(locale.LC_ALL, '')

    # Encoding for output streams
    if str == bytes:  # PY2
        writer = codecs.getwriter(locale.getpreferredencoding())
        o_stdout, o_stderr = sys.stdout, sys.stderr
        sys.stdout = writer(sys.stdout)
        sys.stdout.buffer = o_stdout
        sys.stderr = writer(sys.stderr)
        sys.stderr.buffer = o_stderr
    else:  # PY3
        sys.stdin = sys.stdin.buffer

    # Parses command-line

    # General options
    options = argparse.ArgumentParser(add_help=False)
    options.add_argument('--version', action='version',
                         version="tej version %s" % tej_version)
    options.add_argument('-v', '--verbose', action='count', default=1,
                         dest='verbosity',
                         help="augments verbosity level")

    # Root parser
    parser = argparse.ArgumentParser(
            description="Trivial Extensible Job-submission",
            parents=[options])
    subparsers = parser.add_subparsers(title='commands', metavar='')

    # Destination selection
    options_dest = argparse.ArgumentParser(add_help=False)
    options_dest.add_argument('destination', action='store',
                              help="Machine to SSH into; [user@]host[:port]")
    options_dest.add_argument('--queue', action='store',
                              default=DEFAULT_TEJ_DIR,
                              help="Directory for tej's files")

    # Setup action
    parser_setup = subparsers.add_parser(
            'setup', parents=[options, options_dest],
            help="Sets up tej on a remote machine")
    parser_setup.add_argument('--make-link', action='append',
                              dest='make_link')
    parser_setup.add_argument('--make-default-link', action='append_const',
                              dest='make_link', const=DEFAULT_TEJ_DIR)
    parser_setup.add_argument('--force', action='store_true')
    parser_setup.add_argument('--only-links', action='store_true')
    parser_setup.set_defaults(func=_setup)

    # Submit action
    parser_submit = subparsers.add_parser(
            'submit', parents=[options, options_dest],
            help="Submits a job to a remote machine")
    parser_submit.add_argument('--id', action='store',
                               help="Identifier for the new job")
    parser_submit.add_argument('--script', action='store',
                               help="Relative name of the script in the "
                                    "directory")
    parser_submit.add_argument('directory', action='store',
                               help="Job directory to upload")
    parser_submit.set_defaults(func=_submit)

    # Status action
    parser_status = subparsers.add_parser(
            'status', parents=[options, options_dest],
            help="Gets the status of a job")
    parser_status.add_argument('--id', action='store',
                               help="Identifier of the running job")
    parser_status.set_defaults(func=_status)

    # Download action
    parser_download = subparsers.add_parser(
            'download', parents=[options, options_dest],
            help="Downloads files from finished job")
    parser_download.add_argument('--id', action='store',
                                 help="Identifier of the job")
    parser_download.add_argument('files', action='store',
                                 nargs=argparse.ONE_OR_MORE,
                                 help="Files to download")
    parser_download.set_defaults(func=_download)

    # Kill action
    parser_kill = subparsers.add_parser(
            'kill', parents=[options, options_dest],
            help="Kills a running job")
    parser_kill.add_argument('--id', action='store',
                             help="Identifier of the running job")
    parser_kill.set_defaults(func=_kill)

    # Delete action
    parser_delete = subparsers.add_parser(
            'delete', parents=[options, options_dest],
            help="Deletes a finished job")
    parser_delete.add_argument('--id', action='store',
                               help="Identifier of the finished job")
    parser_delete.set_defaults(func=_delete)

    # List action
    parser_list = subparsers.add_parser(
            'list', parents=[options, options_dest],
            help="Lists remote jobs")
    parser_list.set_defaults(func=_list)

    args = parser.parse_args()
    setup_logging(args.verbosity)

    try:
        args.func(args)
    except Error as e:
        # No need to show a traceback here, this is not an internal error
        logger.critical(e)
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
