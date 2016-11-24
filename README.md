# CraigsListScraper
Simple scraper for periodical car search on multiple Craiglist's site and emailing notifications about new listings.
The output is stored in local files.
New postings are emailed to provided email account

# Configuration
The only command line parameter for the application is configuration file name.

The configuration contains:
- list of Craigslist sites to be queried
- car search parameters (like price, milage etc.)
- path to output files with search results
- email login credentials for sending emails
- destination email addresses for the notifications

See sample configuration file for more detail

# Usage
The program is intended to be executed periodically (every hour, every day) as scheduled job.
The only required parameter is configruation file name.
