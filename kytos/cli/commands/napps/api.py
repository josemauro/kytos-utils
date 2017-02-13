"""Translate cli commands to non-cli code."""
import logging
import os
import re
from urllib.error import HTTPError

from kytos.utils.napps import NAppsManager

log = logging.getLogger(__name__)


class NAppsAPI:
    """An API for the command-line interface.

    Use the config file only for required options. Static methods are called
    by the parser and they instantiate an object of this class to fulfill the
    request.
    """

    @classmethod
    def disable(cls, args):
        """Disable subcommand."""
        napps = args['<napp>']
        mgr = NAppsManager()
        for napp in napps:
            mgr.set_napp(*napp)
            log.info('NApp %s:', mgr.napp_id)
            cls.disable_napp(mgr)

    @staticmethod
    def disable_napp(mgr):
        """Disable a NApp."""
        if mgr.is_enabled():
            log.info('  Disabling...')
            mgr.disable()
        log.info('  Disabled.')

    @classmethod
    def enable(cls, args):
        """Enable subcommand."""
        napps = args['<napp>']
        mgr = NAppsManager()
        for napp in napps:
            mgr.set_napp(*napp)
            log.info('NApp %s:', mgr.napp_id)
            cls.enable_napp(mgr)

    @staticmethod
    def enable_napp(mgr):
        """Install one NApp using NAppManager object."""
        try:
            if not mgr.is_enabled():
                log.info('  Enabling...')
                mgr.enable()
            log.info('  Enabled.')
        except (FileNotFoundError, PermissionError) as e:
            log.error('  %s', e)

    @classmethod
    def create(cls, args):
        """Bootstrap a basic NApp structure on the current folder."""
        NAppsManager.create_napp()

    @classmethod
    def uninstall(cls, args):
        """Uninstall and delete NApps.

        For local installations, do not delete code outside install_path and
        enabled_path.
        """
        napps = args['<napp>']
        mgr = NAppsManager()
        for napp in napps:
            mgr.set_napp(*napp)
            log.info('NApp %s:', mgr.napp_id)
            if mgr.is_installed():
                log.info('  Uninstalling...')
                mgr.uninstall()
                cls.disable_napp(mgr)
            log.info('  Uninstalled.')

    @classmethod
    def install(cls, args):
        """Install local or remote NApps."""
        mgr = NAppsManager()
        for napp in args['<napp>']:
            mgr.set_napp(*napp)
            log.info('NApp %s:', mgr.napp_id)
            if not mgr.is_installed():
                cls.install_napp(mgr)
            else:
                log.info('  Installed.')

    @classmethod
    def install_napp(cls, mgr):
        """Install a NApp."""
        try:
            log.info('  Searching local NApp...')
            mgr.install_local()
            log.info('  Installed.')
            cls.enable_napp(mgr)
        except FileNotFoundError:
            log.info('  Downloading from NApps Server...')
            try:
                mgr.install_remote()
                log.info('  Installed.')
                cls.enable_napp(mgr)
            except HTTPError as e:
                if e.code == 404:
                    log.error('  NApp not found.')
                else:
                    log.error('  NApps Server error: %s', e)

    @classmethod
    def search(cls, args):
        """Search for NApps in NApps server matching a pattern."""
        safe_shell_pat = re.escape(args['<pattern>']).replace(r'\*', '.*')
        pat_str = '.*{}.*'.format(safe_shell_pat)
        pattern = re.compile(pat_str, re.IGNORECASE)
        remote_json = NAppsManager.search(pattern)

        mgr = NAppsManager()
        enabled = mgr.get_enabled()
        installed = mgr.get_installed()
        remote = (((n['author'], n['name']), n['description'])
                  for n in remote_json)

        napps = []
        for napp, desc in sorted(remote):
            status = 'i' if napp in installed else '-'
            status += 'e' if napp in enabled else '-'
            status = '[{}]'.format(status)
            name = '{}/{}'.format(*napp)
            napps.append((status, name, desc))
        cls.print_napps(napps)

    @classmethod
    def list(cls, args):
        """List all installed NApps and inform whether they are installed."""
        mgr = NAppsManager()

        # Add status
        napps = [napp + ('[ie]',) for napp in mgr.get_enabled()]
        napps += [napp + ('[i-]',) for napp in mgr.get_disabled()]

        # Sort, add description and reorder coloumns
        napps.sort()
        napps = [(s, '{}/{}'.format(u, n), mgr.get_description(u, n))
                 for u, n, s in napps]

        cls.print_napps(napps)

    @staticmethod
    def print_napps(napps):
        """Print status, name and description."""
        if not napps:
            print('No NApps found.')
            return

        stat_w = 6  # We already know the size of Status col
        name_w = max(len(n[1]) for n in napps)
        desc_w = max(len(n[2]) for n in napps)
        term_w = os.popen('stty size', 'r').read().split()[1]
        remaining = int(term_w) - stat_w - name_w - 6
        desc_w = min(desc_w, remaining)
        widths = (stat_w, name_w, desc_w)

        header = '\n{:^%d} | {:^%d} | {:^%d}' % widths
        row = '{:^%d} | {:<%d} | {:<%d}' % widths
        print(header.format('Status', 'NApp ID', 'Description'))
        print('=+='.join('=' * w for w in widths))
        for user, name, desc in napps:
            desc = (desc[:desc_w-3] + '...') if len(desc) > desc_w else desc
            print(row.format(user, name, desc))

        print('\nStatus: (i)nstalled, (e)nabled\n')