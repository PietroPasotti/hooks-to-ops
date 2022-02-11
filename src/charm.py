#!/usr/bin/env python3
# Copyright 2022 Erik Lonroth <erik.lonroth@gmail.com>
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Microsample service charm.
"""

import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

from ops.charm import CharmBase
from ops.main import main
from ops.model import ActiveStatus, MaintenanceStatus, BlockedStatus, Relation
from subprocess import check_call, check_output

from charms.operator_libs_linux.v0 import systemd
from charms.operator_libs_linux.v1 import snap


logger = logging.getLogger(__name__)


def get_output(cmd: str) -> str:
    return check_output(cmd.split(' ')).decode('ascii')


class MicrosampleCharm(CharmBase):
    """Microsample service charm."""
    _service_name = "snap.microsample.microsample.service"

    def __init__(self, *args):
        super().__init__(*args)
        fw = self.framework
        fw.observe(self.on.install, self._on_install)
        fw.observe(self.on.stop, self._on_stop)

        fw.observe(self.on.config_changed, self._on_config_changed)
        fw.observe(self.on.update_status, self._on_update_status)
        fw.observe(self.on.upgrade_charm, self._on_upgrade_charm)

        fw.observe(self.on.website_relation_joined,
                   self._on_website_relation_joined)

        # TODO: add Requires for HTTP relation

    def _on_install(self, _event):
        """Install and start the microsample snap.
        """
        
        self.unit.status = MaintenanceStatus('installing microsample')
        # this will automatically start the service.
        microsample_snap = self._refresh_snap()

        # snap.channel is actually a version string e.g. "v10.1"
        # this might fire a "socket.timeout: timed out" error
        # if the snap hasn't quite finished installing yet.
        check_call(["application-version-set", 
                    microsample_snap.channel.strip('v')])

        # might be a few seconds before the service 
        # actually comes up in the background
        self.unit.status = ActiveStatus()

    def _on_config_changed(self, _event):
        """Updates the service on config change.
        """
        self.unit.status = MaintenanceStatus('Configuring charm')
        # the only config options are port and address, so either 
        # way we always need to update the snap.
        # we assume the snap is smart enough to not restart 
        # if the values aren't *actually* different.
        port = self.port
        microsample_snap = snap.SnapCache()["microsample"]
        microsample_snap.set({'port': port, 'address': self.host})

        # ensure all opened ports are closed #idempotence
        open_ports = get_output('opened-ports')
        for open_port in filter(None, open_ports.split('\n')):
            check_call(["close-port", open_port])

        # ensure only the port we need is
        check_call(["open-port", port])

        # restart the service
        systemd.service_restart("snap.microsample.microsample.service")

        # port and host have an impact on relation data, so *if* we do 
        # have a website relation, we need to update its databag
        if relation := self._get_website_relation():
            relation.data[self.unit].update(
                {'hostname': self.private_address,
                'port': self.port}
            )

        self.unit.status = ActiveStatus()

    def _on_update_status(self, _event):  
        """Periodically check that the service is accessible.
        """
        # note that this is not at all mandatory, only a demonstration. 
        # We could just as well assume that the service is up and running, 
        # since if the snap.ensure had failed, we would have known at 
        # install time
        url = f"http://{self.private_address}:{self.port}"
        error = None

        try:
            response = urlopen(Request(url)).read()
        except URLError as e:
            error = e
            
        if error or not response:
            self.unit.status = BlockedStatus(
                f'application not responding at {url}; {error}'
                )
        
        self.unit.status = ActiveStatus()

    def _on_upgrade_charm(self, _event): 
        """Ensures that the snap is at its latest version.
        """
        self.unit.status = MaintenanceStatus('Upgrading charm')
        self._refresh_snap()
        self.unit.status = ActiveStatus()

    def _on_stop(self, _event):  
        """Stop the service.
        """
        systemd.service_stop(self._service_name)
        self.unit.status = ActiveStatus('Service stopped.')

    def _on_website_relation_joined(self, _event): 
        """Ensure that the relation databag is up to date, 
        whenever the relation is joined.
        """
        self._update_relation_data()

    def _update_relation_data(self):
        """Ensure that the relation databag is up to date.
        """
        relation = self._get_website_relation()
        logger.debug(
            f"{self.unit.name} website settings:\n "
            f"{relation.data}\n"
            "Relation members:"
            f"{relation.units}\n"
        )
        address, port = self.private_address, self.port

        # self.unit.name is microsample/0
        unit_id = self.unit.app.name
        services_spec = {
            '_service_name': 'microsample',
            'service_host': self.host,
            'service_port': port,
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

    # UTILITIES
    @staticmethod
    def _refresh_snap() -> snap.Snap:
        """Ensures that the snap is at its latest version.
        """
        microsample_snap = snap.SnapCache()["microsample"]
        microsample_snap.ensure(snap.SnapState.Latest, channel='edge') 
        return microsample_snap

    def _get_website_relation(self) -> Relation:
        """Return the website relation object.
        NOTE: would return None if called too early, e.g. during install.
        """
        return self.model.get_relation('website')

    @property
    def private_address(self) -> str:
        """we get the private address by reading it off the 'special' juju-info
        relation databag
        """
        return self.model.get_binding("juju-info").network.bind_address

    @property
    def port(self) -> int:
        """The port on which the microserver service will be listening.
        """
        return self.config['port']

    @property
    def host(self) -> str:
        """The host on which the microserver service will be listening.
        """
        return self.config['host']


if __name__ == "__main__":
    main(MicrosampleCharm)
