# user-engagement-metrics

## How to use

1. Put all usernames (one per line) in usernames.txt.
2. Replace YOUR_PERSONAL_ACCESS_TOKEN with your token. (when you create the PAT, no boxes need to be checked for public works and fine grained or classic tokens both work)
3. Run `make install` to install the dependencies needed to run the script.
4. Run the script. `python3 ./user_engagement_metrics.py`. It will create/update:
  - `user_results.jsonl` with your results.
  - `completed_usernames.txt` to track progress.
  - NOTE: If stopped, just run again. It skips completed users when the `completed-usernames.txt` is present.

## Example jsonl output
```json
{"username": "zkoppert", "name": "Zack Koppert", "public_repos": 65, "followers": 340, "following": 81, "organizations": ["github", "InnerSourceCommons", "alltheavo", "super-linter"], "starred_repos": 178, "total_public_prs": 888, "total_public_issues": 287, "total_public_commits": 4666}
```

## Make commands

There are several automated make commands to make using this tool easier!

- `make clean`: This command will remove any temporary cache files
- `make reset`: Use this command to remove the `completed_usernames.txt` file which tracks users you've already completed. It also removes output files such as any `existing user_results.jsonl`.
- `make install`: Installs the needed dependencies to use the tool utilizing `pip install`
- `make test`: Only really for development where you want to run the test suite against the functional code

## License
MIT

## How to file issues and get help

This project uses GitHub issues to track bugs and feature requests. Please search the existing issues before filing new issues to avoid duplicates. For new issues, file your bug or feature request as a new issue.

For help or questions about using this project, please open an issue and a maintainer will respond to you normally within a week.

user-engagement-metrics is under active development and maintained by GitHub staff **AND THE COMMUNITY**. We will do our best to respond to support, feature requests, and community questions in a timely manner but are not under any company SLOs.

## GitHub Support Policy

Support for this project is limited to the resources listed above.
