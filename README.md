# Overview
This charm deploys a flask application and provides the [interface:http] for other charms to relate to it.

The deployed snap is a flask webservice named [microsample]. Here is the code for it: [microsample-flask-snap]. The webservice is the development flask web-server and is a starting point for more production grade implementations.

The snap runs on any linux distribution, which is one of the advantages with snaps. You could consider placing snaps in your IoT devices and deploy them with juju for automated tests and CI/CD pipelines.

This charm is an ugly intermediate step demonstrator meant to show how to use old-school hooks with a new-style `ops`-based charm.
This was developed as material for [this howto][this-howto].

# Stand alone usage
To deploy this charm:
```
juju deploy microsample
juju expose microsample
```
Once the service is "Online", you can get the public ip of the unit as 
given by `juju status` and test by:
```
curl http://[PUBLIC IP]:8080/api/info
curl http://[PUBLIC IP]:8080
```

[this-howto]: http://discourse.charmhub.com
[interface:http]: https://discourse.jujucharms.com/t/interface-layers/1121
[microsample-flask-snap]: https://github.com/erik78se/microsample-flask-snap
[tutorial-a-tiny-hooks-charm]: https://discourse.jujucharms.com/t/tutorial-a-tiny-hooks-charm/1315
[snapcraft.io]: https://snapcraft.io/
[ssl-termination-proxy]: https://jujucharms.com/ssl-termination-proxy
[haproxy]: https://jujucharms.com/haproxy/
[microsample]: https://snapcraft.io/microsample
