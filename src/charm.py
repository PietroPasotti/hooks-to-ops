#!/usr/bin/env python3
import json
import os
import subprocess
import time
import typing
from itertools import islice
from logging import getLogger

from charms.operator_libs_linux.v0 import systemd
from ops.main import main
from ops.charm import CharmBase
from subprocess import check_call, PIPE, Popen, check_output
import pathlib

from ops.model import MaintenanceStatus, ActiveStatus, BlockedStatus, Relation

logger = getLogger("Microsample")


def get_output(cmd):
    process = Popen(cmd, stdout=PIPE)
    return process.communicate()[0].decode('ascii')


class Microsample(CharmBase):
    _service_name = "snap.microsample.microsample.service"
    _default_port = 8080

    def __init__(self, *args):
        super().__init__(*args)
        fw = self.framework
        fw.observe(self.on.config_changed, self._on_config_changed)
        fw.observe(self.on.install, self._on_install)
        fw.observe(self.on.start, self._on_start)
        fw.observe(self.on.stop, self._on_stop)
        fw.observe(self.on.update_status, self._on_update_status)
        fw.observe(self.on.upgrade_charm, self._on_upgrade_charm)
        fw.observe(self.on.website_relation_broken,
                   self._on_website_relation_broken)
        fw.observe(self.on.website_relation_changed,
                   self._on_website_relation_changed)
        fw.observe(self.on.website_relation_departed,
                   self._on_website_relation_departed)
        fw.observe(self.on.website_relation_joined,
                   self._on_website_relation_joined)

    @property
    def private_address(self) -> str:
        """we get the private address by reading it off the 'special' juju-info
        relation databag
        """
        return self.model.get_binding("juju-info").network.bind_address

    @property
    def port(self) -> int:
        return self.config.get('port', self._default_port)

    def wait_service_active(self):
        """sleep until service becomes active"""
        self.unit.status = MaintenanceStatus('waiting for service to come up')
        while not systemd.service_running(self._service_name):
            time.sleep(.5)

    def _get_microsample_version(self):
        snap_info = get_output("snap info microsample")

        def is_version_line(line: str):
            return line.startswith('installed:')

        flipped_snapinfo_lines = reversed(snap_info.split('\n'))
        try:
            version_info = next(filter(is_version_line, flipped_snapinfo_lines))
        except StopIteration:
            raise RuntimeError('microsample not installed')

        # version_info format (example) at this stage:
        # 'installed:          v1.21.9                    (2946) 191MB classic'
        version = next(islice(filter(None, version_info.split(' ')), 1, None))
        return version

    def _on_install(self, _event):
        out = check_call("snap info microsample | grep -c 'installed'")
        is_microsample_installed = bool(out.decode('ascii').strip())

        if not is_microsample_installed:
            self.unit.status = MaintenanceStatus('installing microsample')
            out = check_call("snap install microsample --edge")

        self.wait_service_active()
        self.unit.status = ActiveStatus()

    def _on_config_changed(self, _event):  # noqa
        address, port = self.private_address, self.port

        check_call([f'snap set microsample port={port}',
                    f'snap set microsample address={address}'])

        # ensure all opened ports are closed #idempotence
        open_ports = get_output('opened-ports')
        for open_port in open_ports.split('\n'):
            check_call(["close-port", open_port])

        # ensure only the port we need is
        check_call(["open-port", port])

        # restart the service
        # check_call(["systemctl restart snap.microsample.microsample.service"])
        systemd.service_restart("snap.microsample.microsample.service")

    def _on_start(self, _event):  # noqa
        systemd.service_start(self._service_name)

    def _on_stop(self, _event):  # noqa
        systemd.service_stop(self._service_name)

    @staticmethod
    def _update_app_version():
        raw = get_output("snap list microsample")
        data = tuple(filter(None, raw.replace('\n', ' ').split(' ')))
        assert len(data) == 16, f'microsample not installed, or ' \
                                f'too many versions are. {data}'
        snap_version = data[-5]
        check_call(f"application-version-set {snap_version}")

    def _on_update_status(self, _event):  # noqa
        # this call should probably be put in install/upgrade, since the
        # snap version is unlikely to change on its own
        self._update_app_version()

        url = f"http://{self.private_address}:{self.port}"
        response = check_output(['curl', '-s', url])

        if response:
            self.unit.status = ActiveStatus()
        else:
            self.unit.status = BlockedStatus(
                f'application not responding at {url}'
            )

    def _on_upgrade_charm(self, _event):  # noqa
        self.unit.status = MaintenanceStatus('Upgrading charm')
        self._on_install(_event)
        self._on_config_changed(_event)
        systemd.service_restart(self._service_name)
        self.wait_service_active()
        self._on_update_status(_event)

    def _get_website_relation(self) -> Relation:
        """Helper function for obtaining the website relation object.
        Returns: relation object
        (NOTE: would return None if called too early, e.g. during install).
        """
        return self.model.get_relation('website')

    def _on_website_relation_broken(self, _event):  # noqa
        pass  # nothing to do

    def _on_website_relation_changed(self, _event):  # noqa
        relation = self._get_website_relation()
        logger.debug(
            f"{self.unit.name} website settings changed:\n "
            "Relation Settings:\n"
            f"{relation.data}\n"
            "Relation members:"
            f"{relation.units}\n"
        )
        address, port = self.private_address, self.port
        # self.unit.name is microsample/
        unit_id = self.unit.app.name
        # unitid=$(basename $JUJU_UNIT_NAME)

        services_spec = {
            '_service_name': 'microsample',
            'service_host': '0.0.0.0',
            'service_port': 8080,
            'service_options': [
                'mode http', 'balance leastconn',
                'http-check expect rstring ^Online$'],
            'servers': [
                [f'microsample_unit_{unit_id}', address, port, 'check']]
        }

        relation.data[self.unit].update(
            {'hostname': address,
             'port': port,
             'services': services_spec}
        )

    def _on_website_relation_departed(self, _event):  # noqa
        logger.debug(f"{self.unit.name} departed website relation")

    def _on_website_relation_joined(self, _event):  # noqa
        logger.debug(f"{self.unit.name} joined website relation")

        relation = self._get_website_relation()
        relation.data[self.unit].update(
            {'hostname': self.private_address,
             'port': self.port}
        )


if __name__ == "__main__":
    main(Microsample)
