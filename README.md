# From Hooks to Ops

The branches of this repository contain three versions of `microsample`; a machine charm that deploys a flask application and provides the [interface:http] for other charms to relate to it.

This repository was written as part of a HowTo guide on how to turn a hooks charm into an ops charm: [tutorial-a-tiny-hooks-charm].

Branches:

 - [0-hooks]: the original charm; as forked from [original-microsample].
 - [1-sh-charm]: an ops charm calling out to the sh scripts.
 - [2-py-charm]: an ops charm with some wrapping.
 - [3-py-final]: the final stage, including all meaningful wrapper charm libraries for e.g. snap management and systemd calls.



[original-microsample]: [https://github.com/erik78se/charm-microsample]
[tutorial-a-tiny-hooks-charm]: https://discourse.jujucharms.com/t/tutorial-a-tiny-hooks-charm/1315
[interface:http]: [https://discourse.jujucharms.com/t/interface-layers/1121]

[0-hooks]: [https://github.com/PietroPasotti/hooks-to-ops/tree/0-hooks]
[1-sh-charm]: [https://github.com/PietroPasotti/hooks-to-ops/tree/1-sh-charm]
[2-py-charm]: [https://github.com/PietroPasotti/hooks-to-ops/tree/2-py-charm]
[3-py-final]: [https://github.com/PietroPasotti/hooks-to-ops/tree/3-py-final]