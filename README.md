Překapávač is a web application for collaborative translation of terminology.  It's written with Flask and SQLAlchemy.  The UI is currently only in Czech.

A live version with a translation of Pokémon Red ongoing can be found at https://prekapavac.rattata.top/.

Překapávač is licenced under the ISC license.

## Set up a dev version

Here's a quick way to set up Překapávač.

```
    git clone https://github.com/Sanqui/prekapavac
    virtualenv --python=python3 env
    source env/bin/activate
    pip install -r requirements.txt
    ./download_static.sh
```

Open config.py and put the following dev config in:

```
    DATABASE = "sqlite:///test.db"

    SECRET_KEY = "SECRET_KEY"

    DEBUG = False
    TEMPLATES_AUTO_RELOAD = True

    SITENAME = "Překapávač DEV"
    REGISTER_KEY = "test"
```

Run `python db.py` to generate an empty database.

Start the server with `python app.py`.  Register a new user account.  Use the "test" key while registering.  The first user account will be made administrator.

Now you should be up to speed.
