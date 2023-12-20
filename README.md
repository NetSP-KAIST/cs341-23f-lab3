# Grader for Lab 3: Building Your Own Network with SDN

## How to use

### Initial setup

```
$ vagrant up
$ pip3 install requirements.txt
```

### Grading a single submission for debugging

For grading `task_*.py` in the current folder, run
```
$ python3 main.py --debug
```
This will save `ouput_debug.txt` in the same folder


### Grading multiple submissions, downloaded from Gradescope

submissions should be placed at `/assignment_*****_export/submission_*****/`, where metadata is placed at `/assignment_*****_export/submission_metadata.yml`

Run
```
$ python3 main.py
```

for grading all tasks. output file will be written at `/assignment_*****_export/submission_*****/`

For running single or submissions in index range, run


```
$ python3 main.py --idx 3 # for running 3rd submission only
```
```
$ python3 main.py --idx 5-10 # for running 5,6,7,8,9th submissions only
```

## Grading Task Details

For task 1, running single python3 script is enough

For task 2-5, `pox.py` should be opened first, then grading script should be run