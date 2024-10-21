

## Processing logs
`process_logs.py` selects  logs from raw logs and post-processes them.

To create selected logs yourself you need to call select_logs from process_logs.py.
If applied on such folders as logs_wo_st_503, logs_wo_cr_505, logs_wo_clue_504, instance ids  will not be among selected logs 
as they were not logged initially.
I added instance ids to selected logs manually and fixed the logging in the code/on the server in early May. So all newer logs (since May)
contain instances id.

## Calculating scores

`calculate_wordle_scores.py` 

This file computes scores from selected logs
and saves them in a JSON.

### Comparing scores of models and humans

`compare_scores.py` takes JSON with the scores of each episode 
and computes mean scores, mean scores per categories and closeness scores.




