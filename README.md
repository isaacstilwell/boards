# Boards - a tracker for the custom keyboard space

## Setup

1. Clone this repo and cd into it
2. Copy `example.env`: `cp example.env .env`
3. Run `uv sync`
4. Install and start PostgreSQL, then create a new local database
    - on MacOS with homebrew and zsh, I ran:
    ```
    > brew install postgresql@18
    > brew services start postgresql@18
    > echo 'export PATH="/opt/homebrew/opt/postgresql@18/bin:#PATH"' >> ~/.zshrc
    > createdb boarddb
    > psql boarddb
    > \conninfo
    ```
5. Add the DB url to .env in the DATABASE_URL field. From the `\conninfo` output, the string should be `psql://<Client User>@localhost:<Server Port>/<Database>`.
6. Run `uv run python manage.py migrate` to set up the DB
7. Run `uv run python manage.py scrape` to scrape the sites into the db. You'll need to wait a few minutes for it to complete.
8. Run `uv run python manage.py runserver` to run the server at port :8000
9. Open the app at [http://localhost:8000/](http://localhost:8000/)
10. Optionally schedule cron jobs to scrape threads and clear unmatched uploaded images with `uv run python manage.py scrape` and `uv run python manage.py clearunmappedimages` respectively. [This](https://cronitor.io/guides/python-cron-jobs) is the guide I used. Make sure to cd into the project and use the absolute path to uv. This is a command I added to my crontab:
```3 2 * * * cd /path/to/boards && /path/to/uv run python manage.py scrape```

## Architecture
The app is 100% built in Django. It contains two apps: `accounts` and `threads`. `Accounts` uses django auth to handle all of the authentication-related code- login, logout, signup. `Threads` is more involved and contains the brunt of the app including the `Thread` model that the app is built around, along with all of the web scrapers and page/api routes.
### Scrapers
Each scraper is a subclass of the BaseScraper ABC, which defines the `write()` and `run() methods that write the scraped thread objects as Threads in the database. It also defines some basic helpers- `sleep()` (used to sleep a random amount between each visit to the site being scraped) and `log()` (used to log errors that the scrapers encounter). Lastly, it defines the abstract `fetch()` method, which each scraper needs to implement according to the logic associated with the site being scraped.

There are four scrapers. All four scrapers follow the same general format:
1. open a page that holds a collection of items to be turned into threads
2. extract links for individual listings that will be turned into Threads
3. scrape the listings located at each link extracted in step 1

The most unique is the `GHScraper`:
- GHScraper: used for scraping the popular keyboard forum GeekHack (GH). Because GH is a forum, the scraper needs to handle more patterns and cannot rely on a set template used to define a thread. For this reason, there is heavy abstraction throughout the class, with separate helper methods designed to extract a specific item or set of items from the thread. The most complex of these is the date extraction logic, which looks for tags with exactly two dates, representing the date range for which the GB is active. Much of this logic is extracted into a helper function in `helpers.py`, which tries to extract dates from strings in a variety of formats.

The other three are very similar, as all three of these vendor sites are built via shopify.
- NKScraper: used for scraping [NovelKeys](https://novelkeys.com). The main highlight is price extraction, which it does at the link extraction level rather than at the listing level because prices are not displayed by default on listings. NK also has "configurator" style listings, which has different image formatting from the regular items.
- CKScraper: used for scraping [CannonKeys](https://cannonkeys.com). The main highlight is date extraction because the CK staff is very inconsistent with their date assignment, sometimes including years, sometimes only including one date instead of two, etc. This prompted me to extract date parsing logic from GHScraper into `helpers.py` and add some more logic for handling dates with number-based instead of text-based months.
- DKScraper: used for scraping [Divinikey](https://divinikey.com). The simplest of the vendor sites- similar logic to CK but without the date complications.

### Models
There are three models: `Thread`, `SavedThread`, and `UploadedImage` (in addition to the `User` model that comes out of the box with Django auth).

- The `Thread` model stores all of the scraped and user-created threads that are live on the site. In addition to the scraped fields, it also has some fields for user-created thread support.
- The `SavedThread` model stores the user-thread pairs for any thread saved by a user along with the time it was saved.
- The `UploadedImage` model stores the user uploaded images from the compose screen. It has a `thread` field that can be null, which indicates that the image isn't yet attached to a thread. Unattached images are rendered on the compose screen and are attached to the created thread after the user clicks "post".

### Templates
There are two types of templates: partials and full templates. The full templates are rendered when a user loads a page, and the partials are rendered when they send an htmx request from that page. This is a common pattern with htmx.

### API
The full API is at `threads/views.py`. There are four main page routes: home, wishlist, compose, and detail, and many endpoints that return partials based on htmx requests. These include thread approvals and rejections, image uploads, thread creation, and saving threads. There are also some routes defined in the `accounts` app that render the login and profile pages.
