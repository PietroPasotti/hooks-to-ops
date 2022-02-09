#!/usr/bin/env python3
import os

from charms.operator_libs_linux.v0 import systemd
from ops.main import main
from ops.charm import CharmBase
from subprocess import check_call, PIPE, Popen
import pathlib


class Microsample(CharmBase):
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

    def _on_install(self, _event):
        out = check_call(["snap info microsample | grep -c 'installed'"])
        is_microsample_installed = bool(out.decode('ascii').strip())

        if not is_microsample_installed:
            self.unit.status = MaintenanceStatus('installing microsample')
            out = check_call(["snap install microsample --edge"])

        self.unit.status = ActiveStatus()

    def _on_config_changed(self, _event):  # noqa
        port = self.config.get('port', 8080)
        host = self.config.get('private-address', '0.0.0.0')

        check_call([f'snap set microsample port={port}',
                    f'snap set microsample address={host}'])

        # ensure all opened ports are closed #idempotence
        process = Popen(['opened-ports'], stdout=PIPE)
        open_ports = process.communicate()[0].decode('ascii')
        for open_port in open_ports.split('\n'):
            check_call(["close-port", open_port])

        # ensure only the port we need is
        check_call(["open-port", port])

        # restart the service
        # check_call(["systemctl restart snap.microsample.microsample.service"])
        systemd.service_restart("snap.microsample.microsample.service")


    def _on_start(self, _event):  # noqa
        systemd.service_start("snap.microsample.microsample.service")

    def _on_stop(self, _event):  # noqa
        systemd.service_stop("snap.microsample.microsample.service")

    def _on_update_status(self, _event):  # noqa
        pass

    def _on_upgrade_charm(self, _event):  # noqa
        pass
        # status-set maintenance "Upgrading charm."
        # ./hooks/install
        # ./hooks/config-changed
        # systemctl restart snap.microsample.microsample.service
        # # Wait a few sec so to let service start...
        # sleep 3
        # ./hooks/update-status

    def _on_website_relation_broken(self, _event):  # noqa
        run_hook('website-relation-broken')

    def _on_website_relation_changed(self, _event):  # noqa
        pass
        # juju-log $JUJU_REMOTE_UNIT modified its settings
        # juju-log Relation settings:
        # relation-get
        # juju-log Relation members:
        # relation-listq
        #
        #
        # address=$(unit-get private-address)
        # port=$(config-get port)
        # unitid=$(basename $JUJU_UNIT_NAME)
        #
        # relation-set hostname=$address
        #
        # relation-set port=$port
        #
        # relation-set "services=
        # - { service_name: microsample,
        #     service_host: 0.0.0.0,
        #     service_port: 8080,
        #     service_options: [mode http, balance leastconn, http-check expect rstring ^Online$],
        #     servers: [[microsample_unit_${unitid}, $address, $port, check]]}
        # "


    def _on_website_relation_departed(self, _event):  # noqa
        pass
        # juju-log $JUJU_REMOTE_UNIT departed

    def _on_website_relation_joined(self, _event):  # noqa
        pass
        # set -e
        # # This must be renamed to the name of the relation. The goal here is to
        # # affect any change needed by relationships being formed
        # # This script should be idempotent.
        # juju-log $JUJU_REMOTE_UNIT joined
        #
        # address=$(unit-get private-address)
        # port=$(config-get port)
        #
        # relation-set hostname=$address
        # relation-set port=$port


if __name__ == "__main__":
    main(Microsample)
