# Forem reports

Showing most recent N=100 posts.

## TODO

* Group posts by authors
* Show date of post and how much time has passed since it was posted.
* See and report how much overlap we have between the  items fetched now and the one we already had.
* People with their first posts - Welcome them to DEV
* Posts that are not in English - recommend them to add a language tag.
* People who signed up in the last D=2 days and have more than N=3 posts. Likely SPAM
* People who signed up in the last D=2 days and have posted. These can be either SPAM or we might want to welcome them.

## Add new sites:

Get the API KEYs from the following URLs and add them to the [action secrets](https://github.com/szabgab/forem-reports/settings/secrets/actions) using the keys listed below:

* https://dev.to/settings/extensions `DEV_TO_API_KEY`
* https://community.codenewbie.org/settings/extensions `COMMUNITY_CODENEWBIE_ORG_API_KEY`

* Update `.github/workflows/pages.yml` with the new key.
* Update `report.py` the `hosts` mapping of hostname to title.

