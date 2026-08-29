\# Storage Protocol QA Automation Framework — Architecture Proposal



\*\*Repo:\*\* `automation\_framework\_pytest`

\*\*Author:\*\* Mohan (QA Automation Architect)

\*\*Status:\*\* Proposal — Pre-Implementation

\*\*Base by:\*\* vishwa42git



\---



\## 1. Overview



This document proposes architecture extensions to the existing pytest automation framework base. The goal is to evolve it into a full-featured \*\*storage protocol QA automation framework\*\* capable of validating NFS, CIFS/SMB, and iSCSI protocol stacks across heterogeneous Linux environments (SUSE, Ubuntu, RHEL, etc.), with proper client detection, connection management, and Linux-flavor-aware command translation.



The three additions proposed are:



| # | Addition | Folder | Purpose |

|---|---|---|---|

| 1 | Client Detection | `client/` | Detect test trigger source; set env context |

| 2 | Connection Layer | `conn/` | SSH, console, and other transport connections |

| 3 | Command Abstraction | `commands/` | OS-aware command translation per Linux flavor |



These sit alongside the existing `framework/`, `lib/`, and `tests/` directories.



\---



\## 2. Existing Base (What We're Building On)



```

automation\_framework\_pytest/

├── framework/

│   └── config.py          ← Settings dataclass; reads API\_BASE\_URL, API\_TIMEOUT

├── lib/                   ← shared utilities (helpers, parsers, etc.)

├── tests/                 ← test suite

├── conftest.py            ← root-level fixtures

├── pyproject.toml         ← project metadata and pytest config

├── .gitignore

└── README.md

```



\*\*`framework/config.py` — existing pattern:\*\*

```python

from dataclasses import dataclass

import os



@dataclass(frozen=True)

class Settings:

&#x20;   base\_url: str = "https://jsonplaceholder.typicode.com"

&#x20;   timeout: float = 10.0



&#x20;   @classmethod

&#x20;   def from\_environment(cls) -> "Settings":

&#x20;       return cls(

&#x20;           base\_url=os.getenv("API\_BASE\_URL", cls.base\_url).rstrip("/"),

&#x20;           timeout=float(os.getenv("API\_TIMEOUT", cls.timeout)),

&#x20;       )

```



All new modules must follow this same pattern: frozen dataclasses for config, environment-driven, no hardcoded credentials.



\---



\## 3. Proposed Directory Structure (Full)



```

automation\_framework\_pytest/

│

├── framework/

│   └── config.py                  ← existing: base Settings dataclass

│

├── client/                        ← NEW: trigger source detection

│   ├── \_\_init\_\_.py

│   ├── detector.py                ← detects CI, local, remote trigger

│   ├── env\_loader.py              ← sets env variables per client context

│   └── clients/

│       ├── \_\_init\_\_.py

│       ├── base\_client.py         ← abstract base class

│       ├── local\_client.py        ← developer laptop / direct run

│       ├── jenkins\_client.py      ← Jenkins CI trigger

│       ├── gitlab\_client.py       ← GitLab CI trigger

│       └── github\_client.py       ← GitHub Actions trigger

│

├── conn/                          ← NEW: connection transports

│   ├── \_\_init\_\_.py

│   ├── base\_connection.py         ← abstract base class

│   ├── ssh\_connection.py          ← SSH via paramiko

│   ├── console\_connection.py      ← serial / OOB console

│   ├── rest\_connection.py         ← REST API calls (extends existing)

│   └── connection\_factory.py     ← factory: returns right connection type

│

├── commands/                      ← NEW: OS-aware command translation

│   ├── \_\_init\_\_.py

│   ├── base\_commands.py           ← abstract command interface

│   ├── command\_runner.py          ← executes via conn layer

│   ├── linux/

│   │   ├── \_\_init\_\_.py

│   │   ├── ubuntu.py              ← Ubuntu/Debian command set

│   │   ├── suse.py                ← SUSE/openSUSE command set

│   │   ├── rhel.py                ← RHEL/CentOS/Rocky command set

│   │   └── resolver.py            ← detects OS flavor; returns right class

│   └── protocols/

│       ├── \_\_init\_\_.py

│       ├── nfs\_commands.py        ← NFS-specific commands

│       ├── cifs\_commands.py       ← CIFS/SMB-specific commands

│       └── iscsi\_commands.py      ← iSCSI-specific commands

│

├── lib/                           ← existing utilities

│

├── tests/

│   ├── conftest.py                ← test-level fixtures

│   ├── nfs/

│   │   ├── conftest.py

│   │   ├── test\_nfs\_server.py

│   │   ├── test\_nfs\_client.py

│   │   └── test\_nfs\_mount.py

│   ├── cifs/

│   │   ├── conftest.py

│   │   ├── test\_cifs\_server.py

│   │   └── test\_cifs\_mount.py

│   └── iscsi/

│       ├── conftest.py

│       ├── test\_iscsi\_target.py

│       └── test\_iscsi\_initiator.py

│

├── conftest.py                    ← root conftest: session-scoped fixtures

├── pyproject.toml

├── .gitignore

└── README.md

```



\---



\## 4. Addition 1 — Client Detection (`client/`)



\### Purpose

Determine \*\*how and from where\*\* the test run is being triggered — a developer's laptop, Jenkins, GitLab CI, GitHub Actions — and use that context to:

\- Load the correct environment variables

\- Set logging level and reporting format appropriately

\- Identify the test executor for traceability in reports



\### How It Works



```

Test run starts

&#x20;     │

&#x20;     ▼

detector.py checks environment variables

&#x20;     │

&#x20;     ├── JENKINS\_URL set?          → JenkinsClient

&#x20;     ├── GITLAB\_CI set?            → GitLabClient

&#x20;     ├── GITHUB\_ACTIONS set?       → GitHubClient

&#x20;     └── none of the above         → LocalClient

&#x20;     │

&#x20;     ▼

Selected client calls env\_loader.py

&#x20;     │

&#x20;     ▼

Environment variables set for the session

(STORAGE\_HOST, NFS\_EXPORT\_PATH, TEST\_CREDS, etc.)

```



\### Key Classes



\*\*`client/clients/base\_client.py`\*\*

```python

from abc import ABC, abstractmethod



class BaseClient(ABC):

&#x20;   @abstractmethod

&#x20;   def name(self) -> str:

&#x20;       """Human-readable name of this client."""



&#x20;   @abstractmethod

&#x20;   def load\_env(self) -> None:

&#x20;       """Set environment variables needed for this trigger context."""



&#x20;   @abstractmethod

&#x20;   def is\_active(self) -> bool:

&#x20;       """Return True if this client matches the current environment."""

```



\*\*`client/detector.py`\*\*

```python

from client.clients.jenkins\_client import JenkinsClient

from client.clients.gitlab\_client  import GitLabClient

from client.clients.github\_client  import GitHubClient

from client.clients.local\_client   import LocalClient



CLIENTS = \[JenkinsClient, GitLabClient, GitHubClient, LocalClient]



def detect\_client():

&#x20;   for ClientClass in CLIENTS:

&#x20;       client = ClientClass()

&#x20;       if client.is\_active():

&#x20;           return client

&#x20;   return LocalClient()   # safe fallback

```



\*\*`client/clients/jenkins\_client.py`\*\*

```python

import os

from client.clients.base\_client import BaseClient



class JenkinsClient(BaseClient):

&#x20;   def name(self) -> str:

&#x20;       return "Jenkins"



&#x20;   def is\_active(self) -> bool:

&#x20;       return "JENKINS\_URL" in os.environ



&#x20;   def load\_env(self) -> None:

&#x20;       # Jenkins injects BUILD\_NUMBER, JOB\_NAME, etc.

&#x20;       # Map them to framework-standard names

&#x20;       os.environ.setdefault("TEST\_RUN\_ID",   os.getenv("BUILD\_NUMBER", "unknown"))

&#x20;       os.environ.setdefault("TEST\_RUN\_NAME", os.getenv("JOB\_NAME", "unknown"))

```



\### Integration with conftest.py



```python

\# conftest.py (root)

import pytest

from client.detector import detect\_client



@pytest.fixture(scope="session", autouse=True)

def client\_context():

&#x20;   client = detect\_client()

&#x20;   client.load\_env()

&#x20;   print(f"\\n\[CLIENT] Triggered from: {client.name()}")

&#x20;   yield client

```



\---



\## 5. Addition 2 — Connection Layer (`conn/`)



\### Purpose

Provide a \*\*unified interface\*\* for talking to remote storage hosts regardless of the transport. Tests declare \*what\* they need (a connection to host X), not \*how\* to connect.



\### Connection Types



| Class | Transport | Use Case |

|---|---|---|

| `SSHConnection` | SSH via paramiko | Primary: run shell commands on Linux hosts |

| `ConsoleConnection` | Serial / IPMI / OOB | When SSH is unavailable; early boot, panic state |

| `RESTConnection` | HTTP/HTTPS | Array management APIs, DDMC, ViPR SRM |



\### Key Design



\*\*`conn/base\_connection.py`\*\*

```python

from abc import ABC, abstractmethod



class BaseConnection(ABC):

&#x20;   def \_\_init\_\_(self, host: str, username: str, password: str):

&#x20;       self.host = host

&#x20;       self.username = username

&#x20;       self.password = password



&#x20;   @abstractmethod

&#x20;   def connect(self) -> None: ...



&#x20;   @abstractmethod

&#x20;   def disconnect(self) -> None: ...



&#x20;   @abstractmethod

&#x20;   def execute(self, command: str) -> tuple\[str, str, int]:

&#x20;       """Returns (stdout, stderr, exit\_code)."""



&#x20;   def \_\_enter\_\_(self):

&#x20;       self.connect()

&#x20;       return self



&#x20;   def \_\_exit\_\_(self, \*args):

&#x20;       self.disconnect()

```



\*\*`conn/ssh\_connection.py`\*\*

```python

import paramiko

from conn.base\_connection import BaseConnection



class SSHConnection(BaseConnection):

&#x20;   def connect(self) -> None:

&#x20;       self.\_client = paramiko.SSHClient()

&#x20;       self.\_client.set\_missing\_host\_key\_policy(paramiko.AutoAddPolicy())

&#x20;       self.\_client.connect(self.host, username=self.username,

&#x20;                            password=self.password, timeout=30)



&#x20;   def disconnect(self) -> None:

&#x20;       self.\_client.close()



&#x20;   def execute(self, command: str) -> tuple\[str, str, int]:

&#x20;       \_, stdout, stderr = self.\_client.exec\_command(command)

&#x20;       exit\_code = stdout.channel.recv\_exit\_status()

&#x20;       return stdout.read().decode(), stderr.read().decode(), exit\_code

```



\*\*`conn/connection\_factory.py`\*\*

```python

from conn.ssh\_connection     import SSHConnection

from conn.console\_connection import ConsoleConnection



def get\_connection(conn\_type: str, host: str, \*\*kwargs):

&#x20;   registry = {

&#x20;       "ssh":     SSHConnection,

&#x20;       "console": ConsoleConnection,

&#x20;   }

&#x20;   cls = registry.get(conn\_type)

&#x20;   if not cls:

&#x20;       raise ValueError(f"Unknown connection type: {conn\_type}")

&#x20;   return cls(host=host, \*\*kwargs)

```



\### Fixture Integration



```python

\# conftest.py

import pytest

from conn.connection\_factory import get\_connection



@pytest.fixture(scope="module")

def nfs\_server\_conn():

&#x20;   conn = get\_connection(

&#x20;       conn\_type=os.getenv("CONN\_TYPE", "ssh"),

&#x20;       host=os.getenv("NFS\_SERVER\_HOST"),

&#x20;       username=os.getenv("HOST\_USER"),

&#x20;       password=os.getenv("HOST\_PASS"),

&#x20;   )

&#x20;   conn.connect()

&#x20;   yield conn

&#x20;   conn.disconnect()

```



\---



\## 6. Addition 3 — Command Abstraction (`commands/`)



\### Purpose

Storage protocol commands differ across Linux distributions. The same logical operation — "install NFS packages", "start NFS service", "mount an NFS share" — uses different binaries and package names on Ubuntu vs SUSE vs RHEL.



The `commands/` layer \*\*translates intent into the correct command string\*\* for the detected OS, then executes it via the `conn/` layer.



\### The Problem It Solves



```

Logical intent: "Install NFS client packages"



Ubuntu:   apt-get install -y nfs-common

SUSE:     zypper install -y nfs-client

RHEL:     dnf install -y nfs-utils

```



Without this layer, test code would be littered with `if distro == "ubuntu"` branches. With it, tests call `nfs.install\_client()` and the framework handles the rest.



\### OS Detection



\*\*`commands/linux/resolver.py`\*\*

```python

from conn.base\_connection import BaseConnection



def detect\_os\_flavor(conn: BaseConnection) -> str:

&#x20;   """

&#x20;   Reads /etc/os-release on the remote host and returns

&#x20;   a normalized flavor string: 'ubuntu', 'suse', 'rhel'

&#x20;   """

&#x20;   stdout, \_, \_ = conn.execute("cat /etc/os-release")

&#x20;   if "ubuntu" in stdout.lower():

&#x20;       return "ubuntu"

&#x20;   if "suse" in stdout.lower():

&#x20;       return "suse"

&#x20;   if "rhel" in stdout.lower() or "centos" in stdout.lower():

&#x20;       return "rhel"

&#x20;   raise RuntimeError(f"Unsupported OS. /etc/os-release output:\\n{stdout}")

```



\### OS Command Classes



\*\*`commands/base\_commands.py`\*\*

```python

from abc import ABC, abstractmethod



class BaseOSCommands(ABC):

&#x20;   """Defines the standard command interface all OS flavors must implement."""



&#x20;   @abstractmethod

&#x20;   def install(self, package: str) -> str: ...



&#x20;   @abstractmethod

&#x20;   def start\_service(self, service: str) -> str: ...



&#x20;   @abstractmethod

&#x20;   def stop\_service(self, service: str) -> str: ...



&#x20;   @abstractmethod

&#x20;   def service\_status(self, service: str) -> str: ...



&#x20;   @abstractmethod

&#x20;   def mount(self, src: str, dst: str, options: str = "") -> str: ...



&#x20;   @abstractmethod

&#x20;   def umount(self, path: str) -> str: ...

```



\*\*`commands/linux/ubuntu.py`\*\*

```python

from commands.base\_commands import BaseOSCommands



class UbuntuCommands(BaseOSCommands):

&#x20;   def install(self, package: str) -> str:

&#x20;       return f"apt-get install -y {package}"



&#x20;   def start\_service(self, service: str) -> str:

&#x20;       return f"systemctl start {service}"



&#x20;   def stop\_service(self, service: str) -> str:

&#x20;       return f"systemctl stop {service}"



&#x20;   def service\_status(self, service: str) -> str:

&#x20;       return f"systemctl status {service}"



&#x20;   def mount(self, src: str, dst: str, options: str = "") -> str:

&#x20;       opts = f"-o {options}" if options else ""

&#x20;       return f"mount {opts} {src} {dst}"



&#x20;   def umount(self, path: str) -> str:

&#x20;       return f"umount {path}"

```



\*\*`commands/linux/suse.py`\*\*

```python

from commands.base\_commands import BaseOSCommands



class SUSECommands(BaseOSCommands):

&#x20;   def install(self, package: str) -> str:

&#x20;       return f"zypper install -y {package}"



&#x20;   def start\_service(self, service: str) -> str:

&#x20;       return f"systemctl start {service}"   # systemd same as Ubuntu



&#x20;   def stop\_service(self, service: str) -> str:

&#x20;       return f"systemctl stop {service}"



&#x20;   def service\_status(self, service: str) -> str:

&#x20;       return f"systemctl status {service}"



&#x20;   def mount(self, src: str, dst: str, options: str = "") -> str:

&#x20;       opts = f"-o {options}" if options else ""

&#x20;       return f"mount {opts} {src} {dst}"



&#x20;   def umount(self, path: str) -> str:

&#x20;       return f"umount -l {path}"            # lazy umount preferred on SUSE

```



\### Protocol Command Layer



\*\*`commands/protocols/nfs\_commands.py`\*\*

```python

from commands.base\_commands import BaseOSCommands



class NFSCommands:

&#x20;   """

&#x20;   NFS-specific logical commands built on top of OS-level commands.

&#x20;   OS-agnostic: receives the OS commands object at construction.

&#x20;   """

&#x20;   PACKAGE\_MAP = {

&#x20;       "ubuntu": "nfs-common",

&#x20;       "suse":   "nfs-client",

&#x20;       "rhel":   "nfs-utils",

&#x20;   }

&#x20;   SERVER\_PACKAGE\_MAP = {

&#x20;       "ubuntu": "nfs-kernel-server",

&#x20;       "suse":   "nfs-kernel-server",

&#x20;       "rhel":   "nfs-utils",

&#x20;   }



&#x20;   def \_\_init\_\_(self, os\_cmd: BaseOSCommands, os\_flavor: str):

&#x20;       self.\_os = os\_cmd

&#x20;       self.\_flavor = os\_flavor



&#x20;   def install\_client(self) -> str:

&#x20;       pkg = self.PACKAGE\_MAP\[self.\_flavor]

&#x20;       return self.\_os.install(pkg)



&#x20;   def install\_server(self) -> str:

&#x20;       pkg = self.SERVER\_PACKAGE\_MAP\[self.\_flavor]

&#x20;       return self.\_os.install(pkg)



&#x20;   def start\_server(self) -> str:

&#x20;       return self.\_os.start\_service("nfs-server")



&#x20;   def export\_share(self, path: str, client\_cidr: str,

&#x20;                    options: str = "rw,sync,no\_subtree\_check") -> str:

&#x20;       return f'echo "{path} {client\_cidr}({options})" >> /etc/exports \&\& exportfs -ra'



&#x20;   def mount\_share(self, server\_ip: str, export: str,

&#x20;                   mount\_point: str, version: int = 4) -> str:

&#x20;       return self.\_os.mount(

&#x20;           src=f"{server\_ip}:{export}",

&#x20;           dst=mount\_point,

&#x20;           options=f"nfsvers={version}"

&#x20;       )



&#x20;   def verify\_mount(self, mount\_point: str) -> str:

&#x20;       return f"mountpoint -q {mount\_point} \&\& echo MOUNTED || echo NOT\_MOUNTED"



&#x20;   def unmount(self, mount\_point: str) -> str:

&#x20;       return self.\_os.umount(mount\_point)

```



\### Command Runner — Ties It All Together



\*\*`commands/command\_runner.py`\*\*

```python

from conn.base\_connection    import BaseConnection

from commands.linux.resolver import detect\_os\_flavor

from commands.linux.ubuntu   import UbuntuCommands

from commands.linux.suse     import SUSECommands

from commands.linux.rhel     import RHELCommands



OS\_COMMAND\_MAP = {

&#x20;   "ubuntu": UbuntuCommands,

&#x20;   "suse":   SUSECommands,

&#x20;   "rhel":   RHELCommands,

}



class CommandRunner:

&#x20;   def \_\_init\_\_(self, conn: BaseConnection):

&#x20;       self.\_conn = conn

&#x20;       flavor = detect\_os\_flavor(conn)

&#x20;       self.\_os\_cmd = OS\_COMMAND\_MAP\[flavor]()

&#x20;       self.flavor = flavor



&#x20;   def run(self, command: str) -> tuple\[str, str, int]:

&#x20;       stdout, stderr, rc = self.\_conn.execute(command)

&#x20;       return stdout, stderr, rc



&#x20;   def run\_and\_assert(self, command: str) -> str:

&#x20;       stdout, stderr, rc = self.run(command)

&#x20;       assert rc == 0, f"Command failed (rc={rc})\\nCMD: {command}\\nSTDERR: {stderr}"

&#x20;       return stdout



&#x20;   @property

&#x20;   def os(self):

&#x20;       return self.\_os\_cmd

```



\### Test Usage (End Result)



```python

\# tests/nfs/test\_nfs\_mount.py



def test\_nfs\_mount\_succeeds(nfs\_server\_runner, nfs\_client\_runner):

&#x20;   nfs = NFSCommands(nfs\_server\_runner.os, nfs\_server\_runner.flavor)



&#x20;   # Install and start NFS server

&#x20;   nfs\_server\_runner.run\_and\_assert(nfs.install\_server())

&#x20;   nfs\_server\_runner.run\_and\_assert(nfs.start\_server())

&#x20;   nfs\_server\_runner.run\_and\_assert(

&#x20;       nfs.export\_share("/exports/vol1", "192.168.1.0/24")

&#x20;   )



&#x20;   # Mount from client

&#x20;   nfs\_client = NFSCommands(nfs\_client\_runner.os, nfs\_client\_runner.flavor)

&#x20;   nfs\_client\_runner.run\_and\_assert(nfs\_client.install\_client())

&#x20;   nfs\_client\_runner.run\_and\_assert(

&#x20;       nfs\_client.mount\_share("192.168.1.10", "/exports/vol1", "/mnt/nfs1")

&#x20;   )



&#x20;   # Verify

&#x20;   stdout, \_, \_ = nfs\_client\_runner.run(nfs\_client.verify\_mount("/mnt/nfs1"))

&#x20;   assert "MOUNTED" in stdout

```



No `if distro ==` anywhere in test code. Tests are clean and readable.



\---



\## 7. How All Three Layers Interact



```

Test Run Triggered

&#x20;       │

&#x20;       ▼

┌───────────────────┐

│   client/         │  Detects trigger source (Jenkins/GitLab/Local)

│   detector.py     │  Loads env vars for this context

└────────┬──────────┘

&#x20;        │ env vars available

&#x20;        ▼

┌───────────────────┐

│   conn/           │  Opens SSH / Console / REST connection

│   ssh\_connection  │  to NFS server, NFS client, iSCSI target, etc.

└────────┬──────────┘

&#x20;        │ connection object

&#x20;        ▼

┌───────────────────┐

│   commands/       │  Detects OS flavor on remote host

│   command\_runner  │  Translates logical commands → OS-specific strings

│   nfs\_commands    │  Executes via conn layer

└────────┬──────────┘

&#x20;        │ stdout, stderr, rc

&#x20;        ▼

┌───────────────────┐

│   tests/          │  Asserts expected outcomes

│   test\_nfs\_mount  │  Fully readable, no OS branching

└───────────────────┘

```



\---



\## 8. Environment Variables Reference



All configuration flows through environment variables, consistent with the existing `Settings` pattern in `framework/config.py`.



| Variable | Used By | Description |

|---|---|---|

| `API\_BASE\_URL` | existing | REST base URL |

| `API\_TIMEOUT` | existing | REST timeout |

| `CONN\_TYPE` | conn/ | `ssh` or `console` |

| `NFS\_SERVER\_HOST` | conn/ | IP/hostname of NFS server |

| `NFS\_CLIENT\_HOST` | conn/ | IP/hostname of NFS client |

| `ISCSI\_TARGET\_HOST` | conn/ | iSCSI target IP |

| `CIFS\_SERVER\_HOST` | conn/ | CIFS server IP |

| `HOST\_USER` | conn/ | Username for SSH |

| `HOST\_PASS` | conn/ | Password for SSH |

| `TEST\_RUN\_ID` | client/ | Set by CI; build number |

| `TEST\_RUN\_NAME` | client/ | Set by CI; job name |



A `.env.example` file will be provided at the root so developers can copy and fill locally.



\---



\## 9. Dependencies to Add to `pyproject.toml`



```toml

\[project.dependencies]

paramiko = ">=3.4"          # SSH connections

pytest   = ">=8.0"          # test runner (existing)



\[project.optional-dependencies]

dev = \[

&#x20;   "pytest-mock>=3.14",

&#x20;   "pytest-cov>=5.0",

&#x20;   "python-dotenv>=1.0",   # .env file loading for local dev

]

```



\---



\## 10. Implementation Phases



\### Phase 1 — Connection Layer (`conn/`)

Foundation everything else sits on. No tests can run against real hosts without it.

\- `base\_connection.py`

\- `ssh\_connection.py`

\- `console\_connection.py`

\- `connection\_factory.py`

\- Unit tests using `pytest-mock` to stub `paramiko`



\### Phase 2 — Command Abstraction (`commands/`)

Depends on Phase 1. OS detection requires an active connection.

\- `base\_commands.py`

\- `linux/ubuntu.py`, `linux/suse.py`, `linux/rhel.py`

\- `linux/resolver.py`

\- `command\_runner.py`

\- Protocol commands: `nfs\_commands.py`, `cifs\_commands.py`, `iscsi\_commands.py`

\- Unit tests: assert correct command strings per OS flavor (no real host needed)



\### Phase 3 — Client Detection (`client/`)

Depends on Phase 1 and 2. Env vars must be loaded before connections are made.

\- `detector.py`

\- `clients/local\_client.py`, `jenkins\_client.py`, `gitlab\_client.py`, `github\_client.py`

\- `env\_loader.py`

\- Unit tests: mock `os.environ` to simulate each CI context



\### Phase 4 — Protocol Tests (`tests/`)

Depends on all three layers. Integration tests against real or containerised hosts.

\- `tests/nfs/` — server config, client config, mount, read/write, unmount

\- `tests/cifs/` — server config, share creation, mount, auth

\- `tests/iscsi/` — target config, initiator discovery, login, block device



\---



\## 11. Open Questions Before Implementation



| Question | Options | Decision Needed By |

|---|---|---|

| SSH key auth vs password? | Both; key preferred | Phase 1 |

| Console transport: serial port or IPMI/iDRAC? | Likely both | Phase 1 |

| Should `commands/` support Windows clients for CIFS? | Descope for now? | Phase 2 |

| OS detection: `/etc/os-release` only, or also `uname`? | `/etc/os-release` preferred | Phase 2 |

| Secrets management: env vars only or Vault/CyberArk? | Env vars for now, Vault later | Phase 3 |

| Test data (server IPs) in env vars or a YAML topology file? | YAML topology preferred | Phase 4 |



\---



\*This proposal covers architecture and interface design only. No implementation exists yet. Actual code will follow Phase 1 through Phase 4 above pending team review.\*

