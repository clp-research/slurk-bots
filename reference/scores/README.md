

## Processing logs
`process_logs.py` selects  logs from raw logs and post-processes them.

To create selected logs yourself you need to call select_logs from process_logs.py.
If applied on the folder "logs_ref_509" instance ids  will not be among selected logs 
as they were not logged initially.
I added instance ids to selected logs manually and fixed the logging in the code/on the server in early May. So all newer logs (since May)
contain instances id.

## Calculating scores

`calculate_reference_metrics.py` 

This file computes scores from selected logs
and saves them in a JSON file. Besides, 
it creates a JSON file with human expressions.

### Comparing scores of models and humans

`visualize.py` takes JSON files with the scores of each episode, computes average metrics,
and plots the results. 

`plot_vocab.py` plots most frequent words used by the model/the humans
 based on JSON files with expressions.




