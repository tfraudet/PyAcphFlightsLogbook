![GitHub Release Date](https://img.shields.io/github/release-date/tfraudet/PyAcphFlightsLogbook) ![GitHub last commit](https://img.shields.io/github/last-commit/tfraudet/PyAcphFlightsLogbook)

# PyAcphFlightsLogbook

Flight **logbook** for **glider** written in Python that automates detection of takeoff and landing events (airfield and schedule) by processing the APRS traffic from the [Open Glider Network](http://wiki.glidernet.org/).
As the program tracks event at aircraft level he can detect landing and takefoff on different airfields. Due to several technical reasons, the detected start and landing times are approximate only. The accuracy is around 1 or 2 minutes.

This is a work in progress. Currently, in addition to takoff and landing events, the tool detects the launch method (aerotowing, self-launching or winch launching) and in the case of a towing, identifies the tow plane. It calculates also the flight duration.

:warning: to date winch lauching detection functionality is not yet fully operational.

Futur releases could have additional features :

* outlanding detection and location
* detection of the runway used for takeoff & landing
* ...

## Usage

Executing the logbook python program is straight forward. It supports 2 arguments that are optionals. For the prerequisites before launching the programm see the [installation](#installation) section

``` bash
# execute the tool with default config file ./acph-logbook.ini
python3 acph-logbook.py

# or with a specific config file
python3 acph-logbook.py -i path-to-my-config-file.ini
```

Example to get the help

``` bash
# get the help
python3 acph-logbook.py -h

#this will return the following output
usage: acph-logbook.py [-h] [-i CONFIG_FILE]

ACPH Glider flight logbook daemon

optional arguments:
  -h, --help            show this help message and exit
  -i CONFIG_FILE, --ini CONFIG_FILE path to the ini config file, default value is ./acph-logbook.ini
```

## Configuration

The program uses a configuration file to initalize settings related to database connection, logging behavior, APRS connection & filtering, and other general settings.

The section `[logbook_general]` is used to initialize general parameters for the logbook

> Pending: :confused: to do!

The section `[aprs]` is used to initialize  parameters relataed to APRS serveur connection and APRS messages filtering

> Pending: :confused: to do!

The section `[mysql_connector_python]` is used to initialize parametr for database conenction

``` ini
[mysql_connector_python]
database = <database-name>
user = <user>
password = <password>
host = <ip adress or dns name>
```

The sections for logging configuration are the standard ones of python logger package. see [logging.config](https://docs.python.org/3/library/logging.config.html) python documentation for more information. The default configuration logs messages up to INFO level in the log file `./logs/acph-aprs.log'` and message up to WARNING level on a slack channel (using webhook Slack API).

``` ini
...
[handlers]
keys=fileHandler,slackHandler

[handler_fileHandler]
class=FileHandler
level=INFO
formatter=acphFormatter
args=('./logs/acph-aprs.log',)

[handler_slackHandler]
class=slack_logger.SlackHandler
level=WARNING
formatter=acphSlackFormatter
args=('Put your webhook URL here',)
...
```

## Installation

The program requires Python 3. It has been developed and test only with Python 3.8.5 and Python 3.7.3

``` bash
# To know your python 3 version
python3 -V
```

### Download & install python dependencies

The logbook python program requires the following python packages. These packages have to be accessible through PYTHONPATH.

* geographiclib v1.50
* geopy v2.0.0
* mysql-connector-python v8.0.21
* ogn-client v0.9.7
* pid v3.0.4
* slack-logger v0.3.1

The best option it's to install them using pip. As for example:

```bash
pip3 install geopy
```

### Configure the MySql database

By default the programm use a MySql database to store the results. Assuming you have already a MySql database running, run the script ```setup_db.py``` to initialize the required tables. This need to be done only once when the database structure evolved or to create tables. The script uses ```acph-logbook.ini``` configuration file to get database connection parameters

```bash
python3 ./setup_db.py
```

## Working principles

* process in realtime OGN APRS message
* for each aircraft detect events like takeoff and landing and store it in a database
* keep xx day of retention in the database
* relay on following resources
  * The [OGN database](http://ddb.glidernet.org/) to identify the aircraft (type, model,...)
  * The xx airport database (altitude, coordinnate,...) to identify takeoff and landing airfields
