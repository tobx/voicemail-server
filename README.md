# Voicemail Server

A VoIP voicemail server that registers with a SIP endpoint, handles incoming calls, logs call activity, records voicemails, and sends email notifications. It allows users to keep their phone number and stay informed about incoming calls without requiring a SIP phone.


## Setup

Run `scripts/setup.sh` to set up the voicemail server.

**Note:** Run `scripts/setup.sh --help` to see the available setup options.


## Configuration

See the example configuration file `config.template.toml`.

The SIP account and password can also be provided through the `VOICEMAIL_SERVER_SIP_ACCOUNT` and `VOICEMAIL_SERVER_SIP_PASSWORD` environment variables, respectively.

A configuration file must be specified using the `--config` option when [starting the server](#start-the-server) unless the server was [installed](#installation).

### Greeting message

Specify a custom greeting message:

```bash
uv run -- voicemail-server --greeting "path/to/greeting.wav"
```

**Note:** The file will be imported into the application's data directory.

### Contacts

Import a [vCard](https://www.rfc-editor.org/info/rfc6350/) file to display contact names in notifications:

```bash
uv run -- voicemail-server --contacts "path/to/contacts.vcf"
```


## Start the server

After running the [Setup](#setup) script and [configuring](#configuration) the server, start it with:

```bash
uv run -- voicemail-server --config "path/to/config.toml"
```


## Installation

Before the installation, run `scripts/install.sh --help` to see the available installation options.

**Note:** Run `scripts/install.sh --info` to display the paths and configurations that will be affected by the installation.

Install the server with `scripts/install.sh`.

After the installation [configure](#configuration) the server. To find the path to the config file, run `scripts/install.sh --info`.

On Debian-like systems, the voicemail server can be run as a service with:

```bash
systemctl enable --now voicemail-server.service
```


## Uninstallation

To uninstall the server, run `scripts/install.sh --uninstall`.


## Development

Run a test server:

1. Run the [setup](#setup) script.

2. Run `test/run.sh` to create the config file `test/config.toml`.

3. Adjust the config file settings.

4. Run `test/run.sh`.


## PJSIP

This application uses PJSIP for VoIP communication.

The available log levels can be found [here](https://docs.pjsip.org/en/latest/specific-guides/other/logging_and_diagnostics.html#choosing-a-log-level).


## Troubleshooting

### Firewall

Firewall ports 4000 and 4001 might need to be opened for incoming UDP traffic.
