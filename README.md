# GETIN-Apply

EVE corp application handler (for the GETIN alliance).

## Requirements

* Python 3.6


## Setup

1. Clone the project
1. Create an app on http://developers.eveonline.com with all the read scopes
1. Copy `config.example.json` to `config.json` in the `app/` directory
1. Edit it with your EVE app info
1. Setup a virtualenv and install the Python dependencies
1. Run the `setup_databse.sh` script
1. Run the `get_sqlite_sde.sh` script
1. Run the `gunicorn_run.sh` script

The app should be running on http://localhost:5000.
