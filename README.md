![GitHub Release Date](https://img.shields.io/github/release-date/tfraudet/PyAcphFlightsLogbook) ![GitHub last commit](https://img.shields.io/github/last-commit/tfraudet/PyAcphFlightsLogbook)

# PyAcphFlightsLogbook

Flight logbook for glider written in pyhton that automates detection of takeoff and landing events (airfield and schedule) by processing the APRS traffic from the [Open Glider Network](http://wiki.glidernet.org/).

This is a work in progress. Currently, in addition to takoff and landing events, the tool detects the launch method (aerotowing, self-launching or winch launching) and in the case of a towing, identifies the tow plane.

:warning: to date winch lauching detection functionality is not yet fully operational.

Futur releases could have additional features :

* detection of the runway used for takeoff & landing
* outlanding detection and location
* ...

## Usage

Executing the logbook python program is straight forward. He support 2 arguments that are optionals.

``` bash
# execute the tool with default config file ./acph-logbook.ini)
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
  -i CONFIG_FILE, --ini CONFIG_FILE
						path to the ini config file, default value is ./acph-logbook.ini
```

## Configuration

## Working principle

* process in realtime OGN APRS message
* for each aircraft detect event like takeoff and landing and store it in a database
* keep xx day of retention in the database
* relay on following resoruces
  * use the OGN dtabase to identify the aircraft (type, model,...)
  * use xx airport database (altitude, coordinnate,...) to identify takeoff and landing airfield

## Implementation @ dependance

database or json