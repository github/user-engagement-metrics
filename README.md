# user-engagement-metrics

## How to use

1. Put all usernames (one per line) in usernames.txt.
2. Replace YOUR_PERSONAL_ACCESS_TOKEN with your token. (when you create the PAT, no boxes need to be checked for public works)
3. Run the script. It will create/update:
  - `user_results.jsonl` with your results.
  - `completed_usernames.txt` to track progress.
  - NOTE: If stopped, just run again. It skips completed users when the `completed-usernames.txt` is present.

## License
MIT