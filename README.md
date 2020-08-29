![GitHub Release Date](https://img.shields.io/github/release-date/tfraudet/PyAcphFlightsLogbook) ![GitHub last commit](https://img.shields.io/github/last-commit/tfraudet/PyAcphFlightsLogbook)

# PyAcphFlightsLogbook

Flight **logbook** for **glider** written in Python that automates detection of takeoff and landing events (airfield and schedule) by processing the APRS traffic from the [Open Glider Network](http://wiki.glidernet.org/).
As the program tracks event at aircraft level he can detect landing and takefoff on different airfields.

This is a work in progress. Currently, in addition to takoff and landing events, the tool detects the launch method (aerotowing, self-launching or winch launching) and in the case of a towing, identifies the tow plane. It calculates also the flight duration.

:warning: to date winch lauching detection functionality is not yet fully operational.

Futur releases could have additional features :

* outlanding detection and location
* detection of the runway used for takeoff & landing
* ...

## Usage

Executing the logbook python program is straight forward. He support 2 arguments that are optionals. For the prerequisites before launching the programm see the [installation](#installation) section

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

## Installation

The program requires Python 3. It has been developed and test only with Python 3.8.5 and Python 3.7.3

``` bash
# To know your python 3 version
python3 -V
```

### Download & install python Dependencies

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

By default the programm use a MySql database to store the results. Assuming you have already a MySql database running, run the script ```setup_db.py``` to initialize the required tables. This need to be done only once when the database structure evolved or to create tables. The script uses acph-loggbook.ini configuration file to get database connection parameters

```bash
python3 ./acph/setup_db.py
```

## Working principles

* process in realtime OGN APRS message
* for each aircraft detect events like takeoff and landing and store it in a database
* keep xx day of retention in the database
* relay on following resources
  * The OGN database to identify the aircraft (type, model,...)
  * The xx airport database (altitude, coordinnate,...) to identify takeoff and landing airfields
